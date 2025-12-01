"""
Dashboard de Producción Odoo - Interfaz Streamlit
"""
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from frontend.stock_view import render_stock_dashboard
from frontend.sales_view import render_sales_dashboard
import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
#  CONFIGURACIÓN
# ==============================
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ==============================
#  CONFIGURACIÓN UI
# ==============================
st.set_page_config(
    page_title="Dashboard Producción Odoo",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded"
)

# Custom CSS for a premium look
st.markdown("""
    <style>
        .main {
            background-color: #0e1117;
        }
        .metric-card {
            background: linear-gradient(145deg, #1e1e1e, #2d2d2d);
            padding: 15px;
            border-radius: 15px;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.5), -5px -5px 15px rgba(50,50,50,0.1);
            text-align: center;
            margin: 10px 0;
            min-height: 100px;
            height: auto;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .metric-label {
            color: #888;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
            line-height: 1.2;
        }
        .metric-value {
            color: #00ff88;
            font-size: 1.3rem;
            font-weight: bold;
            word-wrap: break-word;
            overflow-wrap: break-word;
            word-break: break-word;
            line-height: 1.4;
            max-width: 100%;
            padding: 5px;
        }
        
        /* Multiselect tags - mostrar texto completo */
        [data-baseweb="tag"] {
            max-width: none !important;
            white-space: normal !important;
            height: auto !important;
            min-height: 28px !important;
            padding: 4px 8px !important;
        }
        
        [data-baseweb="tag"] span {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            max-width: none !important;
            word-wrap: break-word !important;
            line-height: 1.3 !important;
        }
        
        /* Contenedor del multiselect */
        [data-baseweb="select"] > div {
            min-height: 44px !important;
            height: auto !important;
        }
        
        .stButton>button {
            background-color: #ff4444;
            color: white;
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
            border: none;
        }
        .stButton>button:hover {
            background-color: #ff3333;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================
#  FUNCIONES API
# ==============================
@st.cache_data(ttl=300)
def search_ofs(start_date: str, end_date: str):
    """Busca órdenes de fabricación por rango de fechas"""
    try:
        response = requests.get(
            f"{API_URL}/of/search",
            params={"start_date": start_date, "end_date": end_date},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al buscar órdenes: {e}")
        return []

@st.cache_data(ttl=300)
def get_of_data(of_id: int):
    """Obtiene el detalle completo de una orden de fabricación"""
    try:
        response = requests.get(
            f"{API_URL}/of/{of_id}",
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener datos de OF: {e}")
        return None

# ==============================
#  FUNCIONES UI
# ==============================
def metric_card(col, label: str, value: str, suffix: str = ""):
    """Renderiza una tarjeta métrica con estilo personalizado"""
    with col:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}{suffix}</div>
            </div>
        """, unsafe_allow_html=True)

def get_name(val):
    """Extrae el nombre de un valor que puede ser dict o False"""
    if isinstance(val, dict):
        return val.get("name", "N/A")
    return "N/A"

# ==============================
#  NAVEGACIÓN ENTRE DASHBOARDS
# ==============================
st.sidebar.title("🧭 Navegación")
st.sidebar.markdown("---")

# Selector de dashboard
dashboard_option = st.sidebar.radio(
    "Seleccionar Dashboard:",
    ["📊 Dashboard de Producción", "📦 Dashboard de Stock", "🚢 Dashboard de Containers"],
    key="dashboard_selector"
)

st.sidebar.markdown("---")

# ==============================
#  DASHBOARD DE PRODUCCIÓN
# ==============================
if dashboard_option == "📊 Dashboard de Producción":
    st.header("🏭 Dashboard de Producción - Órdenes de Fabricación")
    
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
            ofs = search_ofs(str(start_date), str(end_date))
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
                    data = get_of_data(selected_of_id)
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
if dashboard_option == "📊 Dashboard de Producción" and "current_of_data" in st.session_state:
    data = st.session_state["current_of_data"]
    of = data.get("of", {})
    componentes = data.get("componentes", [])
    subproductos = data.get("subproductos", [])
    detenciones = data.get("detenciones", [])
    consumo = data.get("consumo", [])
    kpis = data.get("kpis", {})
    
    # ==============================
    # TARJETAS KPI - Información General
    # ==============================
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
    
    st.markdown("---")
    
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
    
    st.markdown("---")
    
    # KPIs de Producción
    st.subheader("📊 KPIs de Producción")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metric_card(col1, "Producción Total", f"{kpis.get('produccion_total_kg', 0):,.2f}", " kg")
    metric_card(col2, "Rendimiento Real", f"{kpis.get('rendimiento_real_%', 0):.2f}", "%")
    metric_card(col3, "KG/HH Efectiva", f"{kpis.get('kg_por_hh_efectiva', 0):.2f}")
    metric_card(col4, "Consumo MP", f"{kpis.get('consumo_real_mp_kg', 0):,.2f}", " kg")
    
    # ==============================
    # GRAFICO RENDIMIENTO
    # ==============================
    st.subheader("📈 Rendimiento del Proceso")
    
    rendimiento = kpis.get("rendimiento_real_%", 0)
    
    fig_r = go.Figure()
    
    fig_r.add_trace(go.Indicator(
        mode="gauge+number",
        value=rendimiento,
        title={"text": "Rendimiento (%)"},
        gauge={
            "axis": {"range": [0, 120]},
            "bar": {"color": "#00cc66"},
            "steps": [
                {"range": [0, 50], "color": "#ff4444"},
                {"range": [50, 80], "color": "#ffaa00"},
                {"range": [80, 100], "color": "#00cc66"},
                {"range": [100, 120], "color": "#00ff88"}
            ],
            "threshold": {
                "line": {"color": "white", "width": 4},
                "thickness": 0.75,
                "value": 95
            }
        }
    ))
    
    fig_r.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"}
    )
    
    st.plotly_chart(fig_r, use_container_width=True)
    
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
        if componentes:
            # Filtro por categoría (multiselect)
            categorias_comp = sorted(list(set([c.get("product_category_name", "N/A") for c in componentes])))
            categorias_seleccionadas = st.multiselect(
                "Filtrar por Categorías",
                categorias_comp,
                default=categorias_comp,  # Por defecto todas seleccionadas
                key="cat_comp"
            )
            
            # Filtrar datos
            if categorias_seleccionadas:
                componentes_filtrados = [c for c in componentes if c.get("product_category_name", "N/A") in categorias_seleccionadas]
            else:
                componentes_filtrados = []
            
            if componentes_filtrados:
                # Tabla
                df_comp = pd.DataFrame([{
                    "Producto": get_name(c.get("product_id")),
                    "Lote": get_name(c.get("lot_id")),
                    "Cantidad (kg)": c.get("qty_done", 0) or 0,
                    "Ubicación Origen": get_name(c.get("location_id")),
                    "Pallet Origen": get_name(c.get("package_id")),
                    "Categoría": c.get("product_category_name", "N/A")
                } for c in componentes_filtrados])
                st.dataframe(df_comp, use_container_width=True, height=400)
                
                # Gráfico de distribución por producto (dinámico según filtro)
                st.markdown("### 📊 Distribución por Producto")
                producto_dist = {}
                for c in componentes_filtrados:
                    prod_name = get_name(c.get("product_id"))
                    qty = c.get("qty_done", 0) or 0
                    if prod_name in producto_dist:
                        producto_dist[prod_name] += qty
                    else:
                        producto_dist[prod_name] = qty
                
                # Ordenar por cantidad descendente
                sorted_products = sorted(producto_dist.items(), key=lambda x: x[1], reverse=True)
                labels = [p[0] for p in sorted_products]
                values = [p[1] for p in sorted_products]
                
                # Truncar labels muy largos para el pie chart
                short_labels = []
                for label in labels:
                    if len(label) > 30:
                        short_labels.append(label[:27] + "...")
                    else:
                        short_labels.append(label)
                
                fig_comp = go.Figure(data=[go.Pie(
                    labels=short_labels,
                    values=values,
                    hole=0.4,
                    textposition='inside',
                    textinfo='percent',
                    hovertemplate='<b>%{label}</b><br>%{value:.2f} kg<br>%{percent}<extra></extra>',
                    marker=dict(
                        colors=['#00cc66', '#00ff88', '#ffaa00', '#ff4444', '#8844ff', '#44ffff', '#ff44ff', '#cc00ff', '#00ccff', '#ccff00'],
                        line=dict(color='#1e1e1e', width=2)
                    )
                )])
                
                fig_comp.update_layout(
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "white", "size": 11},
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.02,
                        bgcolor="rgba(30,30,30,0.8)",
                        bordercolor="#444",
                        borderwidth=1
                    ),
                    margin=dict(l=20, r=200, t=40, b=20)
                )
                
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # Gráfico de distribución por categoría (dinámico según filtro)
                st.markdown("### 📦 Distribución por Categoría")
                cat_dist = {}
                for c in componentes_filtrados:
                    cat_name = c.get("product_category_name", "N/A")
                    qty = c.get("qty_done", 0) or 0
                    if cat_name in cat_dist:
                        cat_dist[cat_name] += qty
                    else:
                        cat_dist[cat_name] = qty
                
                # Ordenar por cantidad descendente
                sorted_cats = sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)
                cat_labels = [c[0] for c in sorted_cats]
                cat_values = [c[1] for c in sorted_cats]
                
                fig_cat = go.Figure(data=[go.Bar(
                    x=cat_labels,
                    y=cat_values,
                    marker=dict(
                        color='#00cc66',
                        line=dict(color='#00ff88', width=1.5)
                    ),
                    text=[f'{v:.1f} kg' for v in cat_values],
                    textposition='outside',
                    textfont=dict(size=12, color='white'),
                    hovertemplate='<b>%{x}</b><br>%{y:.2f} kg<extra></extra>',
                    width=0.6
                )])
                
                fig_cat.update_layout(
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "white", "size": 12},
                    xaxis=dict(
                        gridcolor="#333",
                        title="",
                        tickangle=-45,
                        tickfont=dict(size=11)
                    ),
                    yaxis=dict(
                        gridcolor="#333",
                        title=dict(text="Cantidad (kg)", font=dict(size=13))
                    ),
                    margin=dict(l=60, r=40, t=40, b=120),
                    bargap=0.3
                )
                
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No hay componentes para las categorías seleccionadas")
        else:
            st.info("No hay componentes registrados")
    
    with tab2:
        if subproductos:
            # Filtro por categoría (multiselect)
            categorias_sub = sorted(list(set([s.get("product_category_name", "N/A") for s in subproductos])))
            categorias_seleccionadas_sub = st.multiselect(
                "Filtrar por Categorías",
                categorias_sub,
                default=categorias_sub,  # Por defecto todas seleccionadas
                key="cat_sub"
            )
            
            # Filtrar datos
            if categorias_seleccionadas_sub:
                subproductos_filtrados = [s for s in subproductos if s.get("product_category_name", "N/A") in categorias_seleccionadas_sub]
            else:
                subproductos_filtrados = []
            
            if subproductos_filtrados:
                # Tabla
                df_sub = pd.DataFrame([{
                    "Producto": get_name(s.get("product_id")),
                    "Lote": get_name(s.get("lot_id")),
                    "Cantidad (kg)": s.get("qty_done", 0) or 0,
                    "Ubicación Destino": get_name(s.get("location_dest_id")),
                    "Pallet Destino": get_name(s.get("result_package_id")),
                    "Categoría": s.get("product_category_name", "N/A")
                } for s in subproductos_filtrados])
                st.dataframe(df_sub, use_container_width=True, height=400)
                
                # Gráfico de distribución por producto (dinámico según filtro)
                st.markdown("### 📊 Distribución por Producto")
                producto_dist_sub = {}
                for s in subproductos_filtrados:
                    prod_name = get_name(s.get("product_id"))
                    qty = s.get("qty_done", 0) or 0
                    if prod_name in producto_dist_sub:
                        producto_dist_sub[prod_name] += qty
                    else:
                        producto_dist_sub[prod_name] = qty
                
                # Ordenar por cantidad descendente
                sorted_products_sub = sorted(producto_dist_sub.items(), key=lambda x: x[1], reverse=True)
                labels_sub = [p[0] for p in sorted_products_sub]
                values_sub = [p[1] for p in sorted_products_sub]
                
                # Truncar labels muy largos
                short_labels_sub = []
                for label in labels_sub:
                    if len(label) > 30:
                        short_labels_sub.append(label[:27] + "...")
                    else:
                        short_labels_sub.append(label)
                
                fig_sub = go.Figure(data=[go.Pie(
                    labels=short_labels_sub,
                    values=values_sub,
                    hole=0.4,
                    textposition='inside',
                    textinfo='percent',
                    hovertemplate='<b>%{label}</b><br>%{value:.2f} kg<br>%{percent}<extra></extra>',
                    marker=dict(
                        colors=['#00ff88', '#00cc66', '#ffaa00', '#ff4444', '#8844ff', '#44ffff', '#ff44ff', '#cc00ff', '#00ccff', '#ccff00'],
                        line=dict(color='#1e1e1e', width=2)
                    )
                )])
                
                fig_sub.update_layout(
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "white", "size": 11},
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.02,
                        bgcolor="rgba(30,30,30,0.8)",
                        bordercolor="#444",
                        borderwidth=1
                    ),
                    margin=dict(l=20, r=200, t=40, b=20)
                )
                
                st.plotly_chart(fig_sub, use_container_width=True)
                
                # Gráfico de distribución por categoría (dinámico según filtro)
                st.markdown("### 📦 Distribución por Categoría")
                cat_dist_sub = {}
                for s in subproductos_filtrados:
                    cat_name = s.get("product_category_name", "N/A")
                    qty = s.get("qty_done", 0) or 0
                    if cat_name in cat_dist_sub:
                        cat_dist_sub[cat_name] += qty
                    else:
                        cat_dist_sub[cat_name] = qty
                
                # Ordenar por cantidad descendente
                sorted_cats_sub = sorted(cat_dist_sub.items(), key=lambda x: x[1], reverse=True)
                cat_labels_sub = [c[0] for c in sorted_cats_sub]
                cat_values_sub = [c[1] for c in sorted_cats_sub]
                
                fig_cat_sub = go.Figure(data=[go.Bar(
                    x=cat_labels_sub,
                    y=cat_values_sub,
                    marker=dict(
                        color='#00ff88',
                        line=dict(color='#00cc66', width=1.5)
                    ),
                    text=[f'{v:.1f} kg' for v in cat_values_sub],
                    textposition='outside',
                    textfont=dict(size=12, color='white'),
                    hovertemplate='<b>%{x}</b><br>%{y:.2f} kg<extra></extra>',
                    width=0.6
                )])
                
                fig_cat_sub.update_layout(
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "white", "size": 12},
                    xaxis=dict(
                        gridcolor="#333",
                        title="",
                        tickangle=-45,
                        tickfont=dict(size=11)
                    ),
                    yaxis=dict(
                        gridcolor="#333",
                        title=dict(text="Cantidad (kg)", font=dict(size=13))
                    ),
                    margin=dict(l=60, r=40, t=40, b=120),
                    bargap=0.3
                )
                
                st.plotly_chart(fig_cat_sub, use_container_width=True)
            else:
                st.info("No hay subproductos para las categorías seleccionadas")
        else:
            st.info("No hay subproductos registrados")
    
    with tab3:
        if detenciones:
            df_det = pd.DataFrame([{
                "Responsable": get_name(d.get("x_studio_responsable")),
                "Motivo": get_name(d.get("x_motivodetencion")),
                "Hora Inicio": d.get("x_horainiciodetencion", "N/A"),
                "Hora Fin": d.get("x_horafindetencion", "N/A"),
                "Horas Detención": d.get("x_studio_horas_de_detencin", 0) or 0
            } for d in detenciones])
            st.dataframe(df_det, use_container_width=True, height=400)
        else:
            st.info("No hay detenciones registradas")
    
    with tab4:
        if consumo:
            # Separar por tipo
            comp_consumo = [c for c in consumo if c.get("type") == "Componente"]
            sub_consumo = [c for c in consumo if c.get("type") == "Subproducto"]
            
            if comp_consumo:
                st.markdown("**Componentes (MP)**")
                df_comp_consumo = pd.DataFrame([{
                    "Pallet": c.get("x_name", "N/A"),
                    "Producto": c.get("x_studio_many2one_field_sPOmE", "N/A"),
                    "Lote": c.get("x_studio_nmero_de_lote", "N/A"),
                    "Hora Inicio": c.get("x_studio_hora_inicio", "N/A"),
                    "Hora Fin": c.get("x_studio_hora_fin", "N/A")
                } for c in comp_consumo])
                st.dataframe(df_comp_consumo, use_container_width=True, height=300)
            
            if sub_consumo:
                st.markdown("**Subproductos**")
                df_sub_consumo = pd.DataFrame([{
                    "Pallet": c.get("x_name", "N/A"),
                    "Producto": c.get("x_studio_many2one_field_sPOmE", "N/A"),
                    "Lote": c.get("x_studio_nmero_de_lote", "N/A"),
                    "Hora Inicio": c.get("x_studio_hora_inicio", "N/A"),
                    "Hora Fin": c.get("x_studio_hora_fin", "N/A")
                } for c in sub_consumo])
                st.dataframe(df_sub_consumo, use_container_width=True, height=300)
        else:
            st.info("No hay horas de consumo registradas")

elif dashboard_option == "📊 Dashboard de Producción":
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

# ==============================
#  DASHBOARD DE STOCK
# ==============================
elif dashboard_option == "📦 Dashboard de Stock":
    render_stock_dashboard()

# ==============================
#  DASHBOARD DE CONTAINERS
# ==============================
elif dashboard_option == "🚢 Dashboard de Containers":
    render_sales_dashboard()

