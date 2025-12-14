import streamlit as st
import pandas as pd
import numpy as np
import io
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except Exception:
    pdfkit = None
    PDFKIT_AVAILABLE = False
import os
from pathlib import Path
from jinja2 import Template
import warnings
import sys

# Suppress FutureWarning about DataFrame concatenation
warnings.simplefilter(action='ignore', category=FutureWarning)

# Importar módulos de autenticación y DB
from auth import require_auth, show_user_info, init_session_state
from etl import load_week_from_db, load_daily_from_db, load_historic_from_db
from matrix_builder import build_matrix, MATRIX_COLUMNS
from pdf_config import (
    get_wkhtmltopdf_path,
    get_wkhtmltopdf_version,
    is_wkhtmltopdf_available,
    get_pdfkit_config
)

# ===============================
# Configuración básica de página
# ===============================
st.set_page_config(
    page_title="Matriz Semanal — Integra SpA",
    layout="wide",
)

# ===============================
# AUTENTICACIÓN REQUERIDA
# ===============================
init_session_state()

if not require_auth():
    st.stop()

# Si llegamos aquí, el usuario está autenticado
show_user_info()

st.title("Matriz Semanal — Integra SpA")
st.caption(f"👤 Sesión activa: {st.session_state.nombre_completo}")

# ===============================
# Cargar datos desde PostgreSQL
# ===============================
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
    if pd.isna(x):
        return ""
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_pesos(x: float) -> str:
    if pd.isna(x):
        return ""
    return "$" + fmt_miles(x)

def fmt_pct(x: float) -> str:
    if pd.isna(x):
        return ""
    return fmt_miles(x) + "%"

# ===============================
# Lógica principal
# ===============================
## FILTRO DE ESTABLECIMIENTOS: SIEMPRE TODOS EN LA MATRIZ SEMANAL
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
    has_total_row = df_matrix["Establecimiento"].eq("Sumas y Promedios").any()
    if has_total_row:
        mask_body = ~df_matrix["Establecimiento"].eq("Sumas y Promedios")
    else:
        mask_body = pd.Series([True] * len(df_matrix), index=df_matrix.index)
    df_body = df_matrix[mask_body].copy()
    df_total = df_matrix[~mask_body].copy()
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
    avg_values = {}
    if not df_total.empty:
        for col in df_total.columns:
            val = df_total.iloc[0][col]
            try:
                avg_values[col] = float(val)
            except:
                avg_values[col] = np.nan
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
        styler.set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', '#E2EFDA'), 
                ('color', 'black'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('border', '3px solid #00C853')  # Verde saturado y más grueso
            ]},
            {'selector': 'td', 'props': [
                ('text-align', 'center'),
                ('border', '3px solid #00C853')  # Verde saturado y más grueso
            ]},
        ])
        # Asegurar bordes verdes aplicados a todo el cuerpo (compatibilidad Streamlit)
        try:
            styler.set_properties(**{'border': '3px solid #00C853'})
        except Exception:
            pass
        def safe_fmt_int(x):
            return f"{int(x)}" if pd.notna(x) else ""
        for internal_col, mi_tuple in col_structure.items():
            if internal_col not in df_body.columns:
                continue
            if internal_col in money_cols:
                styler.format(fmt_pesos, subset=[mi_tuple])
            elif internal_col in pct_cols:
                styler.format(fmt_pct, subset=[mi_tuple])
            elif internal_col in int_cols:
                styler.format(safe_fmt_int, subset=[mi_tuple])
            elif internal_col in float_cols:
                styler.format(fmt_miles, subset=[mi_tuple])
            if internal_col in high_is_good or internal_col in low_is_good:
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
                            # Azul si bueno, Rojo si malo
                            if is_high:
                                if v > avg: c = "#0000FF"  # azul
                                elif v < avg: c = "#FF0000"  # rojo
                            else:
                                if v < avg: c = "#0000FF"  # azul
                                elif v > avg: c = "#FF0000"  # rojo
                            if c:
                                styles.append(f"color: {c}; font-weight: bold;")
                            else:
                                styles.append("")
                        except:
                            styles.append("")
                    return styles
                styler.apply(color_logic, subset=[mi_tuple], axis=0)
        return styler
    
    # CSS para scroll horizontal con columna congelada
    st.markdown("""
    <style>
    /* Contenedor scrolleable con ancho máximo */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
    }
    
    /* Para tablas de dataframe con scroll horizontal */
    [data-testid="stDataFrameContainer"] {
        max-width: 100%;
        overflow-x: auto;
    }
    
    /* Estilos adicionales para mejor visualización */
    [data-testid="stDataFrameContainer"] > div {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Selector de ordenamiento manual
    st.subheader("Matriz semanal")
    
    # Columnas disponibles para ordenar (excluyendo Establecimiento)
    sortable_cols = [c for c in df_body.columns if c != "Establecimiento"]
    col_sort1, col_sort2 = st.columns([2, 1])
    with col_sort1:
        sort_col = st.selectbox(
            "Ordenar por:",
            options=["Establecimiento"] + sortable_cols,
            index=0,
            key="sort_column"
        )
    with col_sort2:
        sort_order = st.radio(
            "Orden:",
            options=["Ascendente", "Descendente"],
            index=0,
            horizontal=True,
            key="sort_order"
        )
    
    # Ordenar df_body según selección del usuario
    ascending = sort_order == "Ascendente"
    df_body_sorted = df_body.sort_values(by=sort_col, ascending=ascending, na_position='last').reset_index(drop=True)
    
    # Unir con sumas y promedios (incluir en la misma tabla)
    if not df_total.empty:
        df_total_aligned = df_total.reindex(columns=df_body_sorted.columns)
        df_full = pd.concat([df_body_sorted, df_total_aligned], ignore_index=True)
    else:
        df_full = df_body_sorted.copy()
    
    df_full_mi = apply_multiindex(df_full)
    styled_full = style_df(df_full_mi.style)
    
    # Calcular altura dinámica: 35px por fila + 100px para headers
    n_rows = len(df_full)
    dynamic_height = n_rows * 35 + 100
    
    # CSS para ocultar scroll del contenedor st-emotion-cache, mantener dvn-scroller
    st.markdown("""
    <style>
    /* Ocultar scroll del contenedor st-emotion-cache interno */
    div[class*="st-emotion-cache-"]::-webkit-scrollbar {
        display: none !important;
    }
    div[class*="st-emotion-cache-"] {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }
    /* Mantener visible el scroll del dvn-scroller */
    .dvn-scroller {
        scrollbar-width: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Mostrar tabla completa (establecimientos + sumas y promedios en una sola tabla)
    st.dataframe(
        styled_full,
        use_container_width=True,
        height=dynamic_height,
        column_config={"_index": None},
    )
    
    # Para Excel: exportar con sumas y promedios
    df_export = df_full.copy()
    
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

    # ----------------------------
    # Generación/Descarga de PDF
    # ----------------------------
    def df_to_html(df):
        # Si es MultiIndex, renderizar MultiIndex como múltiples header rows
        # Usar pandas Styler para formato visual idéntico
        if hasattr(df, 'render'):  # Si es un Styler
            html = df.render()
        else:
            html = df.to_html(index=False, border=0, escape=False)
        template = Template('''
        <html>
        <head>
        <meta charset="utf-8" />
        <style>
        body { background: #fff; font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0; }
        .pdf-table-container { width: 100%; margin: 0; padding: 0; }
        table { border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; }
        th, td { border: 2px solid #00C853 !important; padding: 6px; text-align: center; }
        th { background: #E2EFDA; color: #222; font-weight: bold; }
        .col-decimal { font-variant-numeric: tabular-nums; }
        .col-pesos { color: #1565C0; font-weight: bold; }
        .col-pct { color: #D84315; font-weight: bold; }
        .col-rojo { color: #FF0000; font-weight: bold; }
        .col-azul { color: #0000FF; font-weight: bold; }
        </style>
        </head>
        <body style="margin:0;padding:0;">
        <div class="pdf-table-container">
        {{ table|safe }}
        </div>
        </body>
        </html>
        ''')
        return template.render(table=html)

    def download_pdf(df, filename="matriz_semanal.pdf"):
        # Usar el mismo styler visual que la matriz
        html = df_to_html(styled_full)
        
        # Opción 1: pdfkit no está disponible
        if not PDFKIT_AVAILABLE:
            st.warning("❌ pdfkit no está instalado. Se ofrece descarga en HTML.")
            st.info(f"Instala pdfkit y jinja2 en tu entorno:\n```\npip install pdfkit jinja2\n```")
            st.download_button(
                label="📥 Descargar matriz en HTML",
                data=html.encode('utf-8'),
                file_name=filename.replace('.pdf', '.html'),
                mime="text/html",
            )
            return
        
        # Opción 2: pdfkit disponible pero wkhtmltopdf no
        wk_path = get_wkhtmltopdf_path()
        if not wk_path:
            st.warning("❌ wkhtmltopdf (binario) no está disponible. Se ofrece HTML.")
            st.info("Instala wkhtmltopdf en tu sistema:\n"
                   "- **Windows (Chocolatey):** `choco install wkhtmltopdf -y`\n"
                   "- **Linux:** `apt-get install wkhtmltopdf`\n"
                   "- **macOS:** `brew install wkhtmltopdf`\n\n"
                   "O establece la variable `WKHTMLTOPDF_PATH` en tu `.env` con la ruta completa.")
            st.download_button(
                label="📥 Descargar matriz en HTML",
                data=html.encode('utf-8'),
                file_name=filename.replace('.pdf', '.html'),
                mime="text/html",
            )
            return
        
        # Opción 3: Generar PDF
        try:
            config = get_pdfkit_config()
            options = {
                'page-size': 'A4',
                'orientation': 'Landscape',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None,
            }
            pdf_bytes = pdfkit.from_string(html, False, options=options, configuration=config)
            st.download_button(
                label="📄 Descargar matriz en PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
            )
        except Exception as e:
            # Fallback final: ofrecer HTML si algo falló en la generación
            st.warning(f"❌ No se pudo generar PDF: {e}. Se ofrece HTML.")
            st.download_button(
                label="📥 Descargar matriz en HTML",
                data=html.encode('utf-8'),
                file_name=filename.replace('.pdf', '.html'),
                mime="text/html",
            )

    # Botón de descarga del PDF (tabla completa con sumas)
    download_pdf(df_full_mi, filename=f"matriz_semanal_semana_{current_week or 'NA'}.pdf")

# ==========================================
# PESTAÑA 2: DETALLE DIARIO (CON RLS APLICADO)
# ==========================================
with tab_daily:
    st.info("ℹ️ Esta vista muestra **solo los establecimientos** de las empresas asociadas a tu usuario (RLS aplicado).")
    with st.spinner('Cargando establecimientos disponibles...'):
        try:
            df_daily_all = load_daily_from_db(
                user_id=st.session_state.user_id,
                is_admin=st.session_state.is_admin
            )
            if df_daily_all.empty:
                st.warning("No hay datos diarios disponibles para tus empresas asignadas.")
                st.stop()
            # Filtrar establecimientos solo de empresas del usuario (no admin)
            if st.session_state.is_admin:
                establecimientos_disponibles = sorted(df_daily_all["Establecimiento"].unique())
            else:
                empresas_usuario = [e['nombre'] for e in st.session_state.empresas]
                establecimientos_disponibles = sorted(df_daily_all[df_daily_all["Establecimiento"].isin(
                    df_long[df_long["Empresa"].isin(empresas_usuario)]["Establecimiento"].unique()
                )]["Establecimiento"].unique())
        except Exception as e:
            st.error(f"Error al cargar establecimientos: {e}")
            st.exception(e)
            st.stop()
    selected_est_daily = st.selectbox(
        "Selecciona un establecimiento para ver el detalle:",
        options=establecimientos_disponibles,
        key="daily_est_selector"
    )
    if selected_est_daily:
        df_daily = df_daily_all[df_daily_all["Establecimiento"] == selected_est_daily].copy()
        
        # Filtros en Expander con Columnas
        with st.expander("🔍 Filtros", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                all_cats = sorted(df_daily["CATEGORIA"].dropna().unique()) if "CATEGORIA" in df_daily.columns else []
                selected_cats = st.multiselect(
                    "Filtrar por Categoría:",
                    options=all_cats,
                    default=all_cats,
                    key="daily_cat_selector"
                )
            
            with col2:
                all_concepts = sorted(df_daily["CONCEPTO"].dropna().unique()) if "CONCEPTO" in df_daily.columns else []
                selected_concepts = st.multiselect(
                    "Filtrar por Concepto:",
                    options=all_concepts,
                    default=all_concepts,
                    key="daily_concept_selector"
                )
        
        # Aplicar filtros
        if selected_cats:
            df_daily = df_daily[df_daily["CATEGORIA"].isin(selected_cats)]
        if selected_concepts:
            df_daily = df_daily[df_daily["CONCEPTO"].isin(selected_concepts)]
        
        import re
        date_cols = [c for c in df_daily.columns if re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", str(c))]
        def parse_date(d):
            try:
                return pd.to_datetime(d, dayfirst=True)
            except:
                return pd.Timestamp.max
        date_cols = sorted(date_cols, key=parse_date)
        cols_to_show = ["CATEGORIA", "CONCEPTO"] + date_cols + ["A. TOTAL"]
        available_cols = [c for c in cols_to_show if c in df_daily.columns]
        df_view = df_daily[available_cols].copy()
        if "CATEGORIA" in df_view.columns:
            df_view = df_view.sort_values(["CATEGORIA", "CONCEPTO"])
        else:
            df_view = df_view.sort_values("CONCEPTO")
        numeric_cols = date_cols + ["A. TOTAL"]
        for c in numeric_cols:
            if c in df_view.columns:
                df_view[c] = df_view[c].fillna(0)
        styler_daily = df_view.style
        for c in numeric_cols:
            if c in df_view.columns:
                styler_daily.format(fmt_miles, subset=[c])
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
        st.dataframe(
            styler_daily,
            width=2000,
            height=800
        )
        buffer_daily = io.BytesIO()
        with pd.ExcelWriter(buffer_daily, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="Detalle Diario")
        buffer_daily.seek(0)
        st.download_button(
            label="Descargar detalle diario en Excel",
            data=buffer_daily.getvalue(),
            file_name=f"detalle_diario_{selected_est_daily}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Selecciona un establecimiento.")
