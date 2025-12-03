import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings

# Suppress FutureWarning about DataFrame concatenation
warnings.simplefilter(action='ignore', category=FutureWarning)

from etl import load_week_excel, load_historic_excel
from matrix_builder import build_matrix, MATRIX_COLUMNS

# ===============================
# Configuración básica de página
# ===============================
st.set_page_config(
    page_title="Matriz Semanal — Replica Power BI",
    layout="wide",
)

st.title("Matriz Semanal — Integra SpA")

# ---------------- Semana actual (consolidado) ----------------
uploaded = st.file_uploader(
    "Sube el Excel semanal consolidado (el mismo que usas en Power BI).",
    type=["xlsx", "xls"],
    key="semana",
)

# ---------------- Histórico persistente (opcional) ----------------
uploaded_hist = st.file_uploader(
    "Sube el Excel histórico (HISTORICO PERSISTENTE.xlsx, hoja 'SIC PROM') — opcional.",
    type=["xlsx", "xls"],
    key="hist",
)

df_hist = None
if uploaded_hist is not None:
    try:
        df_hist = load_historic_excel(uploaded_hist)
        st.success("Histórico cargado correctamente.")
        # Solo mostramos un mini resumen para comprobar que cargó
        if {"N° Semana", "Empresa", "Establecimiento", "MDAT"}.issubset(df_hist.columns):
            st.caption(
                f"Histórico: {df_hist['N° Semana'].min()}–{df_hist['N° Semana'].max()} "
                f"({df_hist['Empresa'].nunique()} empresas, "
                f"{df_hist['Establecimiento'].nunique()} establecimientos)."
            )
    except Exception as e:
        st.error(f"No se pudo cargar el histórico: {e}")
        df_hist = None

# ===============================
# Helpers de formato numérico
# ===============================

def fmt_miles(x: float) -> str:
    """Número con separador de miles y coma decimal: 12.345,67"""
    if pd.isna(x):
        return ""
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pesos(x: float) -> str:
    """Igual que arriba, pero con símbolo $ delante."""
    if pd.isna(x):
        return ""
    return "$" + fmt_miles(x)


def fmt_pct(x: float) -> str:
    """Para % que ya vienen como número (no lo dividimos por 100)."""
    if pd.isna(x):
        return ""
    return fmt_miles(x) + "%"


# ===============================
# Lógica principal
# ===============================
if uploaded is not None:
    # 1) ETL → DataFrame "largo" basado en el Excel semanal
    df_long = load_week_excel(uploaded)

    st.success("Archivo semanal cargado correctamente.")

    # 2) Filtro por establecimiento
    all_est = sorted(df_long["Establecimiento"].unique())
    selected_est = st.multiselect(
        "Filtrar por establecimiento",
        options=all_est,
        default=all_est,
    )

    if not selected_est:
        st.warning("Selecciona al menos un establecimiento.")
        st.stop()

    df_long_filtered = df_long[df_long["Establecimiento"].isin(selected_est)].copy()

    # 3) Construir matriz (incluye Sumas y Promedios)
    current_week = None
    if "N° Semana" in df_long.columns:
        try:
            current_week = int(df_long["N° Semana"].dropna().max())
        except:
            pass
            
    if current_week is None:
        import re
        from datetime import datetime
        filename = uploaded.name
        match = re.search(r"(\d{8})_(\d{8})", filename)
        if match:
            date_str = match.group(2)
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
                current_week = dt.isocalendar()[1]
                st.info(f"Semana detectada desde nombre de archivo: {current_week} (Fecha fin: {date_str})")
            except:
                pass

    if current_week:
        st.info(f"Semana detectada en el archivo semanal (ISO/Raw): {current_week}")
    
    # Alineación de semanas
    if df_hist is not None and "N° Semana" in df_hist.columns:
        max_hist_week = df_hist["N° Semana"].max()
        if max_hist_week > 100 and (current_week is None or current_week < 60):
            st.warning(
                f"Detectado posible desface de semanas: Semanal={current_week}, Histórico (max)={max_hist_week}. "
                "Usando la última semana del histórico para alinear los datos."
            )
            current_week = max_hist_week
        elif current_week is None:
            current_week = max_hist_week
            st.info(f"Usando última semana del histórico: {current_week}")
    elif df_hist is not None:
        st.warning("No se detectó columna 'N° Semana' en el semanal. Los comparativos históricos podrían no ser exactos.")
    df_matrix = build_matrix(df_long_filtered, df_hist=df_hist, current_week=current_week).copy()

    if "index" in df_matrix.columns:
        df_matrix.rename(columns={"index": "inc."}, inplace=True)

    # ------------------------------------------
    # 4) Pestañas: Matriz Semanal | Detalle Diario
    # ------------------------------------------
    tab_matrix, tab_daily = st.tabs(["Matriz Semanal", "Detalle Diario"])

    # ==========================================
    # PESTAÑA 1: MATRIZ SEMANAL
    # ==========================================
    with tab_matrix:
        # 3.1 Separar cuerpo vs Sumas y Promedios
        has_total_row = df_matrix["Establecimiento"].eq("Sumas y Promedios").any()
        if has_total_row:
            mask_body = ~df_matrix["Establecimiento"].eq("Sumas y Promedios")
        else:
            mask_body = pd.Series([True] * len(df_matrix), index=df_matrix.index)

        df_body = df_matrix[mask_body].copy()
        df_total = df_matrix[~mask_body].copy()

        # 3.2 Ranking por MDAT
        if "MDAT" in df_body.columns:
            df_body["MDAT"] = pd.to_numeric(df_body["MDAT"], errors="coerce")
            df_body["Ranking MDAT"] = (
                df_body["MDAT"]
                .rank(ascending=False, method="min")
                .astype("Int64")
            )
        else:
            df_body["Ranking MDAT"] = pd.NA

        if not df_total.empty:
            df_total["Ranking MDAT"] = ""

        def insert_ranking_col(df: pd.DataFrame) -> pd.DataFrame:
            cols = list(df.columns)
            if "Ranking MDAT" in cols and "MDAT" in cols:
                cols.remove("Ranking MDAT")
                idx = cols.index("MDAT") + 1
                cols.insert(idx, "Ranking MDAT")
                return df[cols]
            return df

        df_body = insert_ranking_col(df_body)
        if not df_total.empty:
            df_total = insert_ranking_col(df_total)

        # Definición de columnas por tipo
        money_cols = [
            "Costo promedio concentrado", "Costo ración vaca", "Precio de la leche",
            "MDAT", "MDAT 4 sem", "MDAT 52 sem"
        ]
        pct_cols = ["Porcentaje de grasa", "Proteinas", "Porcentaje costo alimentos"]
        int_cols = [
            "Ranking MDAT", "Ranking 4 sem", "Ranking 52 sem",
            "Vacas masa", "Vacas en ordeña", "Vacas 4 sem", "Vacas 52 sem",
            "Grms concentrado / ltr leche"
        ]
        float_cols = [
            "Superficie Praderas", "Carga animal", "Kg MS Concentrado / vaca",
            "Kg MS Conservado / vaca", "Praderas y otros verdes", "Total MS",
            "Producción promedio", "MDAT (L/vaca/día)"
        ]

        def clean_and_convert(df):
            df = df.fillna(np.nan)
            for c in df.columns:
                if c in money_cols or c in pct_cols or c in float_cols:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
                elif c in int_cols:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            return df

        df_body = clean_and_convert(df_body)
        if not df_total.empty:
            df_total = clean_and_convert(df_total)

        # Definición de reglas de negocio para colores:
        high_is_good = [
            "Porcentaje de grasa", "Proteinas", 
            "Producción promedio", "Precio de la leche", 
            "MDAT", "MDAT (L/vaca/día)", 
            "MDAT 4 sem", "MDAT 52 sem"
        ]
        
        low_is_good = [
            "Costo promedio concentrado", 
            "Grms concentrado / ltr leche", 
            "Costo ración vaca", 
            "Porcentaje costo alimentos", 
            "Ranking MDAT", "Ranking 4 sem", "Ranking 52 sem"
        ]

        # Extraer fila de promedios para comparar
        avg_values = {}
        if not df_total.empty:
            for col in df_total.columns:
                val = df_total.iloc[0][col]
                try:
                    avg_values[col] = float(val)
                except:
                    avg_values[col] = np.nan

        # Estructura de columnas para el MultiIndex (Visual)
        col_structure = {
            "Establecimiento": ("", "Establecimiento"),
            "Superficie Praderas": ("", "Superficie de uso ganadero (ha)"),
            "Vacas masa": ("", "Vacas masa"),
            "Vacas en ordeña": ("", "Vacas en ordeña"),
            "Carga animal": ("", "Carga animal"),
            "Porcentaje de grasa": ("", "% Gr"),
            "Proteinas": ("", "% P"),
            "Costo promedio concentrado": ("", "Costo / kg de concentrado (TCO)"),
            "Grms concentrado / ltr leche": ("", "Gramos de MS de concentrado / litro"),
            
            "Kg MS Concentrado / vaca": ("Consumos en Kg. MS / vaca", "Concentrados"),
            "Kg MS Conservado / vaca": ("Consumos en Kg. MS / vaca", "Forrajes conservados"),
            "Praderas y otros verdes": ("Consumos en Kg. MS / vaca", "Pradera y otros verdes"),
            "Total MS": ("Consumos en Kg. MS / vaca", "Total"),
            
            "Producción promedio": ("", "Producción por vaca (L/vaca/día)"),
            "Costo ración vaca": ("", "Costo de la ración ($/vaca/día)"),
            "Precio de la leche": ("", "Precio leche ($/L)"),
            "MDAT (L/vaca/día)": ("", "MDAT (L/vaca/día)"),
            "Porcentaje costo alimentos": ("", "% costo alimentos"),
            "MDAT": ("", "MDAT / vaca / día en $"),
            "Ranking MDAT": ("", "Ranking (por MDAT)"),
            
            "MDAT 4 sem": ("MDAT Prom Últimas 4 Sem", "MDAT / vaca / día en $"),
            "Vacas 4 sem": ("MDAT Prom Últimas 4 Sem", "Vacas en ordeña"),
            "Ranking 4 sem": ("MDAT Prom Últimas 4 Sem", "Ranking"),
            
            "MDAT 52 sem": ("MDAT Prom 12 meses", "MDAT / vaca / día en $"),
            "Vacas 52 sem": ("MDAT Prom 12 meses", "Vacas en ordeña"),
            "Ranking 52 sem": ("MDAT Prom 12 meses", "Ranking"),
        }

        def apply_multiindex(df):
            existing_cols = [c for c in col_structure.keys() if c in df.columns]
            df = df[existing_cols].copy()
            tuples = [col_structure[c] for c in existing_cols]
            df.columns = pd.MultiIndex.from_tuples(tuples)
            return df

        df_body_mi = apply_multiindex(df_body)
        df_total_mi = apply_multiindex(df_total) if not df_total.empty else None

        def style_df(styler):
            # Estilos globales
            styler.set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', '#E2EFDA'), 
                    ('color', 'black'),
                    ('font-weight', 'bold'),
                    ('text-align', 'center'),
                    ('border', '1px solid #70AD47')
                ]},
                {'selector': 'td', 'props': [
                    ('text-align', 'center'),
                    ('border', '1px solid #d3d3d3')
                ]},
            ])
            
            def safe_fmt_int(x):
                return f"{int(x)}" if pd.notna(x) else ""

            # Aplicar formatos y colores condicionales
            for internal_col, mi_tuple in col_structure.items():
                if internal_col not in df_body.columns:
                    continue
                
                # 1. Formatos numéricos
                if internal_col in money_cols:
                    styler.format(fmt_pesos, subset=[mi_tuple])
                elif internal_col in pct_cols:
                    styler.format(fmt_pct, subset=[mi_tuple])
                elif internal_col in int_cols:
                    styler.format(safe_fmt_int, subset=[mi_tuple])
                elif internal_col in float_cols:
                    styler.format(fmt_miles, subset=[mi_tuple])
                
                # 2. Lógica Condicional (Azul vs Rojo)
                if internal_col in high_is_good or internal_col in low_is_good:
                    
                    # Función para aplicar estilo fila por fila
                    def color_logic(s, col_name=internal_col):
                        avg = avg_values.get(col_name, np.nan)
                        if pd.isna(avg):
                            return ["" for _ in s]
                        
                        styles = []
                        is_high = col_name in high_is_good
                        
                        for val in s:
                            try:
                                v = float(val)
                                if pd.isna(v):
                                    styles.append("")
                                    continue
                                
                                c = ""
                                if is_high:
                                    if v > avg: c = "#0000FF" # Azul
                                    elif v < avg: c = "#FF0000" # Rojo
                                else: # Low is good
                                    if v < avg: c = "#0000FF" # Azul
                                    elif v > avg: c = "#FF0000" # Rojo
                                    
                                if c:
                                    styles.append(f"color: {c}; font-weight: bold;")
                                else:
                                    styles.append("")
                            except:
                                styles.append("")
                        return styles

                    styler.apply(color_logic, subset=[mi_tuple], axis=0)

            return styler

        styled_body = style_df(df_body_mi.style)
        styled_total = style_df(df_total_mi.style) if df_total_mi is not None else None

        # 5) Mostrar tablas
        st.subheader("Matriz semanal")

        n_rows = len(df_body)
        height = min(600, 35 * n_rows + 80)

        st.dataframe(
            styled_body,
            width=2000,
            height=height,
        )

        if not df_total.empty:
            st.markdown("### Sumas y Promedios")
            st.dataframe(
                styled_total,
                width=2000,
                height=100,
            )

        # 6) Excel para descarga
        if not df_total.empty:
            df_total_aligned = df_total.reindex(columns=df_body.columns)
            df_export = pd.concat([df_body, df_total_aligned], ignore_index=True)
        else:
            df_export = df_body.copy()

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Matriz semanal")
        buffer.seek(0)

        st.download_button(
            label="Descargar matriz en Excel",
            data=buffer.getvalue(),
            file_name="matriz_semanal.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        
    # ==========================================
    # PESTAÑA 2: DETALLE DIARIO
    # ==========================================
    with tab_daily:
        st.subheader("Detalle Diario por Establecimiento")
        
        # Selector único de establecimiento
        selected_est_daily = st.selectbox(
            "Selecciona un establecimiento para ver el detalle:",
            options=all_est,
            key="daily_est_selector"
        )
        
        if selected_est_daily:
            # Filtrar datos crudos para ese establecimiento
            df_daily = df_long[df_long["Establecimiento"] == selected_est_daily].copy()
            
            # ---------------------------------------------------------
            # Filtro por Categoria
            # ---------------------------------------------------------
            all_cats = sorted(df_daily["CATEGORIA"].dropna().unique()) if "CATEGORIA" in df_daily.columns else []
            selected_cats = st.multiselect(
                "Filtrar por Categoría:",
                options=all_cats,
                default=all_cats,
                key="daily_cat_selector"
            )
            
            if selected_cats:
                df_daily = df_daily[df_daily["CATEGORIA"].isin(selected_cats)]
            
            # Identificar columnas de fecha (dd-mm-yyyy)
            import re
            date_cols = [c for c in df_daily.columns if re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", c)]
            
            # Ordenar columnas de fecha cronológicamente
            def parse_date(d):
                try:
                    return pd.to_datetime(d, dayfirst=True)
                except:
                    return pd.Timestamp.max
            
            date_cols = sorted(date_cols, key=parse_date)
            
            # Columnas a mostrar: Categoria, CONCEPTO, [Fechas], A. TOTAL
            # Aseguramos que existan
            cols_to_show = ["CATEGORIA", "CONCEPTO"] + date_cols + ["A. TOTAL"]
            available_cols = [c for c in cols_to_show if c in df_daily.columns]
            
            df_view = df_daily[available_cols].copy()
            
            # Ordenar por Categoria y Concepto
            if "CATEGORIA" in df_view.columns:
                df_view = df_view.sort_values(["CATEGORIA", "CONCEPTO"])
            else:
                df_view = df_view.sort_values("CONCEPTO")
            
            # Rellenar NaNs con 0 para que se vean los números
            numeric_cols = date_cols + ["A. TOTAL"]
            for c in numeric_cols:
                if c in df_view.columns:
                    df_view[c] = df_view[c].fillna(0)

            # Formateo visual
            # Usamos Styler para dar formato a números
            styler_daily = df_view.style
            
            # Formato miles para fechas y total
            for c in numeric_cols:
                if c in df_view.columns:
                    styler_daily.format(fmt_miles, subset=[c])
            
            # Estilos básicos
            styler_daily.set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', '#f0f2f6'),
                    ('color', 'black'),
                    ('font-weight', 'bold'),
                    ('text-align', 'center')
                ]},
                {'selector': 'td', 'props': [
                    ('text-align', 'center')
                ]},
            ])
            
            # Mostrar tabla
            st.dataframe(
                styler_daily,
                width=2000,
                height=800
            )
        else:
            st.info("Selecciona un establecimiento.")

else:
    st.info("Sube el Excel semanal consolidado para ver la matriz.")
