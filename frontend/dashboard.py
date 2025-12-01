"""
Dashboard de Producción Odoo - Interfaz Streamlit
"""
import streamlit as st
from datetime import date, timedelta

from frontend.config.settings import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS
from frontend.services.api_client import api_client
from frontend.components.kpi_cards import (
    render_general_info, render_po_info, render_kpi_cards
)
from frontend.components.charts import render_rendimiento_gauge
from frontend.components.tables import (
    render_componentes_table, render_subproductos_table,
    render_detenciones_table, render_consumo_table
)


# ==============================
#  CONFIGURACIÓN UI
# ==============================
st.set_page_config(
    page_title=PAGE_TITLE,
    layout=LAYOUT,
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================
#  INPUT
# ==============================
st.title("📦 Producción Odoo – Dashboard Premium")

# --- Sidebar: Selección de OF ---
st.sidebar.header("🔍 Buscar Orden de Fabricación")

# Date filters
col1_date, col2_date = st.sidebar.columns(2)
with col1_date:
    start_date = st.date_input(
        "Desde",
        value=date.today() - timedelta(days=30),
        key="start_date"
    )
with col2_date:
    end_date = st.date_input(
        "Hasta",
        value=date.today(),
        key="end_date"
    )

# Search button
if st.sidebar.button("🔍 Buscar OFs", use_container_width=True):
    with st.spinner("Buscando órdenes de fabricación..."):
        ofs = api_client.search_ofs(str(start_date), str(end_date))
        if ofs:
            st.session_state["ofs_list"] = ofs
            st.success(f"Se encontraron {len(ofs)} órdenes de fabricación")
        else:
            st.warning("No se encontraron órdenes de fabricación en el rango seleccionado")
            st.session_state["ofs_list"] = []

# OF Selection
if "ofs_list" in st.session_state and st.session_state["ofs_list"]:
    ofs_options = {
        f"{of['name']} - {of['product_id']['name'] if isinstance(of.get('product_id'), dict) else 'N/A'}": of['id']
        for of in st.session_state["ofs_list"]
    }
    
    selected_of = st.sidebar.selectbox(
        "Seleccionar Orden de Fabricación",
        options=list(ofs_options.keys()),
        key="selected_of"
    )
    
    selected_of_id = ofs_options[selected_of]
    
    if st.sidebar.button("📥 Cargar OF", use_container_width=True):
        with st.spinner("Cargando datos de la OF..."):
            try:
                data = api_client.get_of_data(selected_of_id)
                if data:
                    st.session_state["current_of_data"] = data
                    st.rerun()
                else:
                    st.error("No se pudieron cargar los datos de la OF")
            except Exception as e:
                st.error(f"Error cargando OF: {e}")

# Clear Cache Button
if st.sidebar.button("🔄 Recargar / Limpiar Caché", use_container_width=True):
    st.cache_data.clear()
    if "current_of_data" in st.session_state:
        del st.session_state["current_of_data"]
    if "ofs_list" in st.session_state:
        del st.session_state["ofs_list"]
    st.rerun()

# ==============================
#  DISPLAY DATA
# ==============================
if "current_of_data" in st.session_state:
    data = st.session_state["current_of_data"]
    of = data.get("of", {})
    componentes = data.get("componentes", [])
    subproductos = data.get("subproductos", [])
    detenciones = data.get("detenciones", [])
    consumo = data.get("consumo", [])
    kpis = data.get("kpis", {})
    
    # ==============================
    # TARJETAS KPI
    # ==============================
    render_general_info(of)
    
    st.markdown("---")
    
    render_po_info(of)
    
    st.markdown("---")
    
    render_kpi_cards(kpis)
    
    # ==============================
    # GRAFICO RENDIMIENTO
    # ==============================
    render_rendimiento_gauge(kpis)
    
    # ==============================
    # TABLAS DE DATOS
    # ==============================
    st.subheader("📋 Detalle de Componentes y Subproductos")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Componentes (MP)",
        "📦 Subproductos",
        "🛑 Detenciones",
        "🕒 Horas de Consumo"
    ])
    
    with tab1:
        render_componentes_table(componentes)
    
    with tab2:
        render_subproductos_table(subproductos)
    
    with tab3:
        render_detenciones_table(detenciones)
    
    with tab4:
        render_consumo_table(consumo)

else:
    st.info("👈 Selecciona un rango de fechas y busca órdenes de fabricación en el panel lateral")
    st.markdown("""
    ### 📊 Bienvenido al Dashboard de Producción
    
    Este dashboard te permite visualizar y analizar datos de órdenes de fabricación de Odoo.
    
    **Características:**
    - 🔍 Búsqueda de OFs por rango de fechas
    - 📈 KPIs de producción y rendimiento
    - 📦 Detalle de componentes y subproductos
    - 🛑 Registro de detenciones
    - 🕒 Control de horas de consumo
    
    **Para comenzar:**
    1. Selecciona un rango de fechas en el panel lateral
    2. Haz clic en "Buscar OFs"
    3. Selecciona una orden de fabricación
    4. Haz clic en "Cargar OF"
    """)
