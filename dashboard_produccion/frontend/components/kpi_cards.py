"""
Componentes de tarjetas KPI
"""
import streamlit as st


def metric_card(col, label: str, value: str, suffix: str = ""):
    """
    Renderiza una tarjeta métrica con estilo personalizado
    
    Args:
        col: Columna de Streamlit donde renderizar
        label: Etiqueta de la métrica
        value: Valor a mostrar
        suffix: Sufijo opcional (ej: "kg", "%")
    """
    with col:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}{suffix}</div>
            </div>
        """, unsafe_allow_html=True)


def render_general_info(of: dict):
    """
    Renderiza las tarjetas de información general de una OF
    
    Args:
        of: Diccionario con datos de la orden de fabricación
    """
    st.subheader("🔹 Información General")
    
    # Fila 1: Datos Básicos
    col1, col2, col3, col4 = st.columns(4)
    
    responsable = of.get("user_id", {})
    responsable_name = responsable.get("name", "N/A") if isinstance(responsable, dict) else "N/A"
    
    cliente = of.get("x_studio_clientes", {})
    cliente_name = cliente.get("name", "N/A") if isinstance(cliente, dict) else "N/A"
    
    product = of.get("product_id", {})
    product_name = product.get("name", "N/A") if isinstance(product, dict) else "N/A"
    
    state = of.get("state", "N/A")
    state_map = {
        "draft": "Borrador",
        "confirmed": "Confirmada",
        "planned": "Planificada",
        "progress": "En Progreso",
        "done": "Finalizada",
        "cancel": "Cancelada"
    }
    state_display = state_map.get(state, state)
    
    metric_card(col1, "Responsable", responsable_name)
    metric_card(col2, "Cliente", cliente_name)
    metric_card(col3, "Producto", product_name)
    metric_card(col4, "Estado", state_display)


def render_po_info(of: dict):
    """
    Renderiza las tarjetas de información de Purchase Order
    
    Args:
        of: Diccionario con datos de la orden de fabricación
    """
    # Fila 2: Datos de PO
    po_cols = st.columns(4)
    
    es_para_po = of.get("x_studio_odf_es_para_una_po_en_particular", False)
    num_po = of.get("x_studio_nmero_de_po_1", "N/A")
    po_asoc = of.get("x_studio_po_asociada", {})
    po_asoc_name = po_asoc.get("name", "N/A") if isinstance(po_asoc, dict) else "N/A"
    kg_totales_po = of.get("x_studio_kg_totales_po", 0) or 0
    
    metric_card(po_cols[0], "¿Para PO?", "Sí" if es_para_po else "No")
    metric_card(po_cols[1], "Número PO", num_po)
    metric_card(po_cols[2], "PO Asociada", po_asoc_name)
    metric_card(po_cols[3], "KG Totales PO", f"{kg_totales_po:,.2f}", " kg")
    
    # Fila 3: Consumos PO
    po_cols2 = st.columns(4)
    kg_consumidos_po = of.get("x_studio_kg_consumidos_po", 0) or 0
    kg_disponibles_po = of.get("x_studio_kg_disponibles_po", 0) or 0
    
    metric_card(po_cols2[0], "KG Consumidos PO", f"{kg_consumidos_po:,.2f}", " kg")
    metric_card(po_cols2[1], "KG Disponibles PO", f"{kg_disponibles_po:,.2f}", " kg")
    metric_card(po_cols2[2], "Dotación", str(of.get("x_studio_dotacin", "N/A")))
    
    sala = of.get("x_studio_sala_de_proceso", {})
    sala_name = sala.get("name", "N/A") if isinstance(sala, dict) else "N/A"
    metric_card(po_cols2[3], "Sala de Proceso", sala_name)


def render_kpi_cards(kpis: dict):
    """
    Renderiza las tarjetas de KPIs calculados
    
    Args:
        kpis: Diccionario con KPIs calculados
    """
    st.subheader("📊 KPIs de Producción")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metric_card(col1, "Producción Total", f"{kpis.get('produccion_total_kg', 0):,.2f}", " kg")
    metric_card(col2, "Rendimiento Real", f"{kpis.get('rendimiento_real_%', 0):.2f}", "%")
    metric_card(col3, "KG/HH Efectiva", f"{kpis.get('kg_por_hh_efectiva', 0):.2f}")
    metric_card(col4, "Consumo MP", f"{kpis.get('consumo_real_mp_kg', 0):,.2f}", " kg")
