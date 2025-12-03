import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings

# Suppress FutureWarning about DataFrame concatenation
warnings.simplefilter(action='ignore', category=FutureWarning)

# Importar nuevos módulos de autenticación y DB
from auth import require_auth, show_user_info, init_session_state
from etl import load_week_from_db, load_daily_from_db, load_historic_from_db
from matrix_builder import build_matrix, MATRIX_COLUMNS

# ===============================
# Configuración básica de página
# ===============================
st.set_page_config(
    page_title="Matriz Semanal — Integra SpA (RLS)",
    layout="wide",
)

# ===============================
# AUTENTICACIÓN REQUERIDA
# ===============================
init_session_state()

if not require_auth():
    st.stop()

# Si llegamos aquí, el usuario está autenticado
# Mostrar info del usuario en sidebar
show_user_info()

st.title("Matriz Semanal — Integra SpA")
st.caption(f"👤 Sesión activa: {st.session_state.nombre_completo}")

# ===============================
# Cargar datos desde PostgreSQL
# ===============================

# Indicador de carga
with st.spinner('Cargando datos desde la base de datos...'):
    try:
        # Cargar datos semanales (SIN RLS - todas las empresas para ranking)
        df_long = load_week_from_db(
            user_id=st.session_state.user_id,
            is_admin=st.session_state.is_admin
        )
        
        # Cargar histórico (para MDAT 4 sem y 52 sem)
        df_hist = load_historic_from_db(
            user_id=st.session_state.user_id,
            is_admin=st.session_state.is_admin
        )
        
        if df_long.empty:
            st.error("No hay datos disponibles en la base de datos.")
            st.stop()
            
        st.success("Datos cargados correctamente desde PostgreSQL.")
        
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.exception(e)
        st.stop()

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

# Filtro por establecimiento
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

# Construir matriz (incluye Sumas y Promedios)
current_week = None
if "N° Semana" in df_long.columns:
    try:
        current_week = int(df_long["N° Semana"].dropna().max())
    except:
        pass

if current_week:
    st.info(f"Semana detectada en los datos: {current_week}")

df_matrix = build_matrix(df_long_filtered, df_hist=df_hist, current_week=current_week).copy()

if "index" in df_matrix.columns:
    df_matrix.rename(columns={"index": "inc."}, inplace=True)

# ------------------------------------------
# Pestañas: Matriz Semanal | Detalle Diario
# ------------------------------------------
tab_matrix, tab_daily = st.tabs(["Matriz Semanal", "Detalle Diario"])

# ==========================================
# PESTAÑA 1: MATRIZ SEMANAL (TODAS LAS EMPRESAS)
# ==========================================
with tab_matrix:
    st.info("ℹ️ Esta vista muestra **todas las empresas** del sistema (sin restricción por usuario).")
    
    # Separar cuerpo vs Sumas y Promedios
    has_total_row = df_matrix["Establecimiento"].eq("Sumas y Promedios").any()
    if has_total_row:
        mask_body = ~df_matrix["Establecimiento"].eq("Sumas y Promedios")
    else:
        mask_body = pd.Series([True] * len(df_matrix), index=df_matrix.index)

    df_body = df_matrix[mask_body].copy()
    df_total = df_matrix[~mask_body].copy()

    # Ranking por MDAT
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

    # Mostrar tablas
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

    # Excel para descarga
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
        label="📥 Descargar matriz en Excel",
        data=buffer.getvalue(),
        file_name="matriz_semanal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    
# ==========================================
# PESTAÑA 2: DETALLE DIARIO (CON RLS APLICADO)
# ==========================================
with tab_daily:
    st.info("ℹ️ Esta vista muestra **solo las empresas** asociadas a tu usuario (RLS aplicado).")
    
    # Cargar lista de establecimientos permitidos para este usuario (con RLS)
    with st.spinner('Cargando establecimientos disponibles...'):
        try:
            # Cargar datos diarios sin filtro de establecimiento para obtener la lista
            df_daily_all = load_daily_from_db(
                user_id=st.session_state.user_id,
                is_admin=st.session_state.is_admin
            )
            
            if df_daily_all.empty:
                st.warning("No hay datos diarios disponibles para tus empresas asignadas.")
                st.stop()
            
            # Extraer establecimientos únicos (ya filtrados por RLS)
            establecimientos_disponibles = sorted(df_daily_all["Establecimiento"].unique())
            
        except Exception as e:
            st.error(f"Error al cargar establecimientos: {e}")
            st.exception(e)
            st.stop()
    
    # Selector de establecimiento
    selected_est_daily = st.selectbox(
        "Selecciona un establecimiento para ver el detalle:",
        options=establecimientos_disponibles,
        key="daily_est_selector"
    )
    
    if selected_est_daily:
        # Filtrar datos para ese establecimiento
        df_daily = df_daily_all[df_daily_all["Establecimiento"] == selected_est_daily].copy()
        
        # Filtro por Categoria
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
        date_cols = [c for c in df_daily.columns if re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", str(c))]
        
        # Ordenar columnas de fecha cronológicamente
        def parse_date(d):
            try:
                return pd.to_datetime(d, dayfirst=True)
            except:
                return pd.Timestamp.max
        
        date_cols = sorted(date_cols, key=parse_date)
        
        # Columnas a mostrar
        cols_to_show = ["CATEGORIA", "CONCEPTO"] + date_cols + ["A. TOTAL"]
        available_cols = [c for c in cols_to_show if c in df_daily.columns]
        
        df_view = df_daily[available_cols].copy()
        
        # Ordenar por Categoria y Concepto
        if "CATEGORIA" in df_view.columns:
            df_view = df_view.sort_values(["CATEGORIA", "CONCEPTO"])
        else:
            df_view = df_view.sort_values("CONCEPTO")
        
        # Rellenar NaNs con 0
        numeric_cols = date_cols + ["A. TOTAL"]
        for c in numeric_cols:
            if c in df_view.columns:
                df_view[c] = df_view[c].fillna(0)

        # Formateo visual
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
        
        # Exportar detalle diario
        buffer_daily = io.BytesIO()
        with pd.ExcelWriter(buffer_daily, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="Detalle Diario")
        buffer_daily.seek(0)

        st.download_button(
            label="📥 Descargar detalle diario en Excel",
            data=buffer_daily.getvalue(),
            file_name=f"detalle_diario_{selected_est_daily}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Selecciona un establecimiento.")
