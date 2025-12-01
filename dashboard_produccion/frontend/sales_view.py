"""
Vista del Dashboard de Containers/Ventas
Diseño responsive y visual mejorado
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
import os
from datetime import date, timedelta

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ==============================
#  ESTILOS CSS PERSONALIZADOS
# ==============================
CUSTOM_CSS = """
<style>
    /* Cards de KPI mejoradas */
    .kpi-container {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    
    .kpi-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 16px;
        padding: 20px;
        flex: 1;
        min-width: 200px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px);
    }
    
    .kpi-icon {
        font-size: 2rem;
        margin-bottom: 10px;
    }
    
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00ff88;
        margin: 5px 0;
    }
    
    .kpi-value.warning {
        color: #ffaa00;
    }
    
    .kpi-value.danger {
        color: #ff4444;
    }
    
    .kpi-label {
        font-size: 0.85rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Container cards */
    .container-card {
        background: linear-gradient(145deg, #1e1e2e, #252535);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #00cc66;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .container-card.warning {
        border-left-color: #ffaa00;
    }
    
    .container-card.danger {
        border-left-color: #ff4444;
    }
    
    .container-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .container-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #fff;
    }
    
    .container-badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-success {
        background: rgba(0, 204, 102, 0.2);
        color: #00cc66;
    }
    
    .badge-warning {
        background: rgba(255, 170, 0, 0.2);
        color: #ffaa00;
    }
    
    .badge-danger {
        background: rgba(255, 68, 68, 0.2);
        color: #ff4444;
    }
    
    .progress-bar-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        height: 12px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-bar-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    /* Info grid */
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin-top: 15px;
    }
    
    .info-item {
        text-align: center;
        padding: 10px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
    }
    
    .info-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
    }
    
    .info-label {
        font-size: 0.75rem;
        color: #888;
        margin-top: 5px;
    }
    
    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 25px 0 15px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    
    .section-icon {
        font-size: 1.5rem;
    }
    
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #fff;
    }
</style>
"""


def get_containers(start_date=None, end_date=None, partner_id=None, state=None):
    """Obtiene lista de containers desde la API"""
    try:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if partner_id:
            params["partner_id"] = partner_id
        if state:
            params["state"] = state
            
        response = requests.get(f"{API_URL}/sales/containers", params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error cargando containers: {e}")
        return []


def get_state_color(avance_pct: float) -> str:
    """Retorna color según el avance"""
    if avance_pct >= 100:
        return "#00ff88"
    elif avance_pct >= 75:
        return "#00cc66"
    elif avance_pct >= 50:
        return "#ffaa00"
    elif avance_pct >= 25:
        return "#ff8800"
    else:
        return "#ff4444"


def get_state_class(avance_pct: float) -> str:
    """Retorna clase CSS según el avance"""
    if avance_pct >= 75:
        return "success"
    elif avance_pct >= 40:
        return "warning"
    else:
        return "danger"


def get_sale_state_display(state: str) -> str:
    """Convierte el estado de venta a texto legible"""
    state_map = {
        "draft": "Borrador",
        "sent": "Enviado",
        "sale": "Confirmado",
        "done": "Completado",
        "cancel": "Cancelado"
    }
    return state_map.get(state, state)


def render_kpi_cards(containers: list):
    """Renderiza las tarjetas de KPI"""
    total_containers = len(containers)
    total_kg = sum([c.get("kg_total", 0) for c in containers])
    total_producidos = sum([c.get("kg_producidos", 0) for c in containers])
    avance_global = (total_producidos / total_kg * 100) if total_kg > 0 else 0
    pendientes = total_kg - total_producidos
    
    # Containers en progreso (avance < 100%)
    en_progreso = len([c for c in containers if 0 < c.get("avance_pct", 0) < 100])
    completados = len([c for c in containers if c.get("avance_pct", 0) >= 100])
    sin_iniciar = len([c for c in containers if c.get("avance_pct", 0) == 0])
    
    avance_class = "" if avance_global >= 50 else "warning" if avance_global >= 25 else "danger"
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-icon">📦</div>
            <div class="kpi-value">{total_containers}</div>
            <div class="kpi-label">Containers Totales</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">🏭</div>
            <div class="kpi-value">{en_progreso}</div>
            <div class="kpi-label">En Producción</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">✅</div>
            <div class="kpi-value">{completados}</div>
            <div class="kpi-label">Completados</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">⏳</div>
            <div class="kpi-value">{sin_iniciar}</div>
            <div class="kpi-label">Sin Iniciar</div>
        </div>
    </div>
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-icon">📊</div>
            <div class="kpi-value {avance_class}">{avance_global:.1f}%</div>
            <div class="kpi-label">Avance Global</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">🎯</div>
            <div class="kpi-value">{total_kg:,.0f}</div>
            <div class="kpi-label">KG Totales</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">✔️</div>
            <div class="kpi-value">{total_producidos:,.0f}</div>
            <div class="kpi-label">KG Producidos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">📋</div>
            <div class="kpi-value warning">{pendientes:,.0f}</div>
            <div class="kpi-label">KG Pendientes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_container_card(container: dict):
    """Renderiza una tarjeta de container"""
    avance = container.get("avance_pct", 0)
    color = get_state_color(avance)
    state_class = get_state_class(avance)
    
    name = container.get("name", "")
    partner = container.get("partner_name", "N/A")
    origin = container.get("origin", "") or "Sin PO"
    producto = container.get("producto_principal", "N/A")
    kg_total = container.get("kg_total", 0)
    kg_producidos = container.get("kg_producidos", 0)
    kg_pendientes = container.get("kg_disponibles", 0)
    num_fab = container.get("num_fabricaciones", 0)
    
    commitment = container.get("commitment_date", "")
    fecha_entrega = commitment[:10] if commitment else "No definida"
    
    st.markdown(f"""
    <div class="container-card {state_class}">
        <div class="container-header">
            <div class="container-title">🚢 {name}</div>
            <div class="container-badge badge-{state_class}">{avance:.1f}% completado</div>
        </div>
        <div style="color: #aaa; margin-bottom: 10px;">
            <strong>Cliente:</strong> {partner} | <strong>PO:</strong> {origin}
        </div>
        <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: {min(avance, 100)}%; background: {color};"></div>
        </div>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-value">{kg_total:,.0f} kg</div>
                <div class="info-label">Total Pedido</div>
            </div>
            <div class="info-item">
                <div class="info-value" style="color: {color};">{kg_producidos:,.0f} kg</div>
                <div class="info-label">Producido</div>
            </div>
            <div class="info-item">
                <div class="info-value">{kg_pendientes:,.0f} kg</div>
                <div class="info-label">Pendiente</div>
            </div>
            <div class="info-item">
                <div class="info-value">{num_fab}</div>
                <div class="info-label">Fabricaciones</div>
            </div>
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
            <span style="color: #888;">📦 Producto:</span> <span style="color: #fff;">{producto}</span>
            <span style="margin-left: 20px; color: #888;">📅 Entrega:</span> <span style="color: #fff;">{fecha_entrega}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_avance_chart(containers: list):
    """Renderiza gráfico de avance por container"""
    if not containers:
        return
    
    # Ordenar por avance
    containers_sorted = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)
    
    names = [f"{c['name']}" for c in containers_sorted]
    avances = [c.get("avance_pct", 0) for c in containers_sorted]
    colors = [get_state_color(a) for a in avances]
    clientes = [c.get("partner_name", "N/A") for c in containers_sorted]
    kg_prod = [c.get("kg_producidos", 0) for c in containers_sorted]
    kg_total = [c.get("kg_total", 0) for c in containers_sorted]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=names,
        x=avances,
        orientation='h',
        marker_color=colors,
        text=[f"{a:.1f}%" for a in avances],
        textposition='outside',
        textfont=dict(size=12, color='white'),
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Avance: %{x:.1f}%<br>'
            'Cliente: %{customdata[0]}<br>'
            'Producido: %{customdata[1]:,.0f} kg<br>'
            'Total: %{customdata[2]:,.0f} kg<extra></extra>'
        ),
        customdata=list(zip(clientes, kg_prod, kg_total))
    ))
    
    # Línea de meta
    fig.add_vline(x=100, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Meta", annotation_position="top")
    
    fig.update_layout(
        height=max(300, len(containers) * 50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 12},
        xaxis=dict(
            title="Avance (%)",
            gridcolor="rgba(255,255,255,0.1)",
            range=[0, max(110, max(avances) + 15)]
        ),
        yaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.05)",
            autorange="reversed"
        ),
        margin=dict(l=10, r=50, t=20, b=40),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_productions_table(productions: list):
    """Renderiza tabla de fabricaciones"""
    if not productions:
        st.info("No hay fabricaciones vinculadas")
        return
    
    df = pd.DataFrame([{
        "OF": p.get("name", ""),
        "Producto": p.get("product_name", "N/A"),
        "Estado": p.get("state_display", ""),
        "KG Planificados": p.get("product_qty", 0),
        "KG Producidos": p.get("qty_produced", 0),
        "Responsable": p.get("user_name", "N/A"),
        "Sala": p.get("sala_proceso", "N/A"),
        "Fecha": p.get("date_planned_start", "")[:10] if p.get("date_planned_start") else "N/A"
    } for p in productions])
    
    st.dataframe(
        df,
        use_container_width=True,
        height=min(400, len(productions) * 40 + 50),
        column_config={
            "KG Planificados": st.column_config.NumberColumn("KG Plan.", format="%,.0f"),
            "KG Producidos": st.column_config.NumberColumn("KG Prod.", format="%,.0f"),
        },
        hide_index=True
    )


def render_detail_gauge(avance: float):
    """Renderiza gauge de avance para el detalle"""
    color = get_state_color(avance)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avance,
        number={"suffix": "%", "font": {"size": 50, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 2, "tickcolor": "white"},
            "bar": {"color": color, "thickness": 0.8},
            "bgcolor": "rgba(255,255,255,0.1)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25], "color": "rgba(255, 68, 68, 0.15)"},
                {"range": [25, 50], "color": "rgba(255, 136, 0, 0.15)"},
                {"range": [50, 75], "color": "rgba(255, 170, 0, 0.15)"},
                {"range": [75, 100], "color": "rgba(0, 204, 102, 0.15)"}
            ],
        }
    ))
    
    fig.update_layout(
        height=250,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        margin=dict(l=30, r=30, t=30, b=10)
    )
    
    return fig


def render_sales_dashboard():
    """Renderiza el dashboard de containers/ventas"""
    
    # Inyectar CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #fff; margin: 0;">🚢 Dashboard de Containers</h1>
        <p style="color: #888; margin-top: 10px;">Seguimiento de producción por pedido de venta</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Sidebar: Filtros ---
    st.sidebar.markdown("### 🔍 Filtros")
    
    # Botón de búsqueda principal
    if st.sidebar.button("🔄 Cargar Containers", use_container_width=True, type="primary"):
        st.session_state["load_containers"] = True
        if "containers_data" in st.session_state:
            del st.session_state["containers_data"]
    
    st.sidebar.markdown("---")
    
    # Filtro de estado
    state_options = {
        "Todos": None,
        "Borrador": "draft",
        "Confirmado": "sale",
        "Completado": "done"
    }
    selected_state = st.sidebar.selectbox(
        "Estado del Pedido",
        options=list(state_options.keys()),
        key="sales_state_filter"
    )
    
    # --- Cargar datos ---
    if st.session_state.get("load_containers", False) or "containers_data" not in st.session_state:
        with st.spinner("🔄 Cargando containers desde Odoo..."):
            containers = get_containers(state=state_options[selected_state])
            st.session_state["containers_data"] = containers
            st.session_state["load_containers"] = False
    
    containers = st.session_state.get("containers_data", [])
    
    if not containers:
        st.markdown("""
        <div style="text-align: center; padding: 50px; background: rgba(255,255,255,0.05); border-radius: 15px; margin: 20px 0;">
            <div style="font-size: 4rem; margin-bottom: 20px;">📦</div>
            <h3 style="color: #fff;">No hay containers con fabricaciones</h3>
            <p style="color: #888;">Haz clic en "Cargar Containers" para buscar pedidos con fabricaciones vinculadas.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # --- KPIs ---
    render_kpi_cards(containers)
    
    st.markdown("---")
    
    # --- Layout principal: 2 columnas ---
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.markdown('<div class="section-header"><span class="section-icon">📊</span><span class="section-title">Avance por Container</span></div>', unsafe_allow_html=True)
        render_avance_chart(containers)
    
    with col_right:
        st.markdown('<div class="section-header"><span class="section-icon">📋</span><span class="section-title">Resumen Rápido</span></div>', unsafe_allow_html=True)
        
        # Top 3 containers más avanzados
        sorted_containers = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)[:3]
        
        for c in sorted_containers:
            avance = c.get("avance_pct", 0)
            color = get_state_color(avance)
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 3px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600;">{c.get('name', '')}</span>
                    <span style="color: {color}; font-weight: 700;">{avance:.1f}%</span>
                </div>
                <div style="color: #888; font-size: 0.85rem; margin-top: 5px;">
                    {c.get('partner_name', 'N/A')} • {c.get('num_fabricaciones', 0)} fab.
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- Lista de Containers ---
    st.markdown('<div class="section-header"><span class="section-icon">🚢</span><span class="section-title">Detalle de Containers</span></div>', unsafe_allow_html=True)
    
    # Selector de container
    container_options = {f"{c['name']} - {c['partner_name']} ({c['avance_pct']:.1f}%)": c for c in containers}
    
    selected_key = st.selectbox(
        "Seleccionar container para ver detalle:",
        options=list(container_options.keys()),
        key="container_detail_selector"
    )
    
    if selected_key:
        selected = container_options[selected_key]
        
        # Card del container seleccionado
        render_container_card(selected)
        
        # Detalle en 2 columnas
        st.markdown("---")
        
        col_gauge, col_prods = st.columns([1, 2])
        
        with col_gauge:
            st.markdown("#### 📈 Avance de Producción")
            fig_gauge = render_detail_gauge(selected.get("avance_pct", 0))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Info adicional
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-top: 10px;">
                <div style="margin-bottom: 10px;">
                    <span style="color: #888;">Estado Venta:</span><br>
                    <span style="color: #fff; font-weight: 600;">{get_sale_state_display(selected.get('state', ''))}</span>
                </div>
                <div style="margin-bottom: 10px;">
                    <span style="color: #888;">Monto Total:</span><br>
                    <span style="color: #00ff88; font-weight: 600;">${selected.get('amount_total', 0):,.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_prods:
            st.markdown(f"#### 🏭 Fabricaciones Vinculadas ({len(selected.get('productions', []))})")
            render_productions_table(selected.get("productions", []))

