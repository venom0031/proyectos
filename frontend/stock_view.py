"""
Vista del Dashboard de Stock - Cámaras
Diseño premium con gráfico interactivo y lista dinámica de lotes
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ==============================
#  ESTILOS CSS PERSONALIZADOS
# ==============================
STOCK_CSS = """
<style>
    /* KPIs */
    .stock-kpi-container {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    
    .stock-kpi-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 14px;
        padding: 16px 20px;
        flex: 1;
        min-width: 140px;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-align: center;
    }
    
    .stock-kpi-icon { font-size: 1.6rem; margin-bottom: 6px; }
    .stock-kpi-value { font-size: 1.4rem; font-weight: 700; color: #00ff88; }
    .stock-kpi-label { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
    
    /* Indicador de cámara encima del gráfico */
    .chamber-indicator {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 8px 4px;
        background: linear-gradient(145deg, #1e1e2e, #252535);
        border-radius: 10px;
        margin: 2px;
        min-width: 100px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .chamber-indicator-name {
        font-size: 0.75rem;
        font-weight: 600;
        color: #fff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 120px;
    }
    
    .chamber-indicator-stats {
        font-size: 0.65rem;
        color: #00ff88;
        margin-top: 4px;
    }
    
    .chamber-indicator-bar {
        width: 100%;
        height: 6px;
        background: rgba(255,255,255,0.1);
        border-radius: 3px;
        margin-top: 6px;
        overflow: hidden;
    }
    
    .chamber-indicator-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    /* Lista de lotes dinámica */
    .lot-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        margin: 6px 0;
        background: linear-gradient(145deg, #1e1e2e, #252535);
        border-radius: 10px;
        border-left: 4px solid;
        transition: transform 0.2s ease;
    }
    
    .lot-item:hover {
        transform: translateX(5px);
    }
    
    .lot-info {
        flex: 1;
    }
    
    .lot-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: #fff;
    }
    
    .lot-product {
        font-size: 0.75rem;
        color: #888;
        margin-top: 2px;
    }
    
    .lot-stats {
        text-align: right;
    }
    
    .lot-qty {
        font-size: 1rem;
        font-weight: 700;
        color: #00ff88;
    }
    
    .lot-date {
        font-size: 0.7rem;
        margin-top: 2px;
    }
    
    .lot-pallets {
        font-size: 0.7rem;
        color: #888;
    }
    
    /* Sección */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 20px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    
    .section-icon { font-size: 1.3rem; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #fff; }
    
    /* Selector de categoría activa */
    .category-selector {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 15px 0;
    }
    
    .category-chip {
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.8rem;
        cursor: pointer;
        border: 1px solid rgba(255,255,255,0.2);
        background: rgba(255,255,255,0.05);
        color: #ccc;
        transition: all 0.2s ease;
    }
    
    .category-chip:hover {
        background: rgba(255,255,255,0.1);
        color: #fff;
    }
    
    .category-chip.active {
        background: linear-gradient(145deg, #00cc66, #00aa55);
        color: #fff;
        border-color: #00cc66;
    }
    
    /* Colores de antigüedad */
    .age-fresh { color: #00ff88 !important; }  /* < 1 mes - Verde */
    .age-ok { color: #88ff00 !important; }     /* 1-3 meses - Verde-Amarillo */
    .age-warning { color: #ffaa00 !important; } /* 3-6 meses - Naranja */
    .age-old { color: #ff6b6b !important; }     /* 6-12 meses - Rojo claro */
    .age-critical { color: #ff0000 !important; } /* > 1 año - Rojo */
</style>
"""

# Paleta de colores para categorías (más variada y distinguible)
CATEGORY_COLORS = [
    '#00cc66', '#ff6b6b', '#ffaa00', '#8844ff', 
    '#00ccff', '#ff44ff', '#44ffff', '#ccff00', 
    '#ff8800', '#88ff00', '#cc00ff', '#00ff88',
    '#ff4488', '#44ff88', '#8888ff', '#ffff44'
]


def get_stock_data():
    """Obtiene datos de stock desde la API"""
    try:
        response = requests.get(f"{API_URL}/stock/dashboard", timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error cargando datos de stock: {e}")
        return []


def get_pallets(location_id, category=None):
    """Obtiene pallets de una ubicación"""
    try:
        params = {"location_id": location_id}
        if category:
            params["category"] = category
        
        response = requests.get(f"{API_URL}/stock/pallets", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error cargando pallets: {e}")
        return []


def get_lots_by_category(category: str, location_ids: list = None):
    """Obtiene lotes agrupados por categoría"""
    try:
        params = {"category": category}
        if location_ids:
            params["location_ids"] = ",".join(str(x) for x in location_ids)
        
        response = requests.get(f"{API_URL}/stock/lots", params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error cargando lotes: {e}")
        return []


def get_age_class(days: int) -> tuple:
    """Retorna clase CSS y color según antigüedad"""
    if days < 30:
        return "age-fresh", "#00ff88", "< 1 mes"
    elif days < 90:
        return "age-ok", "#88ff00", "1-3 meses"
    elif days < 180:
        return "age-warning", "#ffaa00", "3-6 meses"
    elif days < 365:
        return "age-old", "#ff6b6b", "6-12 meses"
    else:
        return "age-critical", "#ff0000", "> 1 año"


def render_kpis(chambers_data: list):
    """Renderiza KPIs de stock"""
    total_chambers = len(chambers_data)
    total_kg = sum([sum(c.get("stock_data", {}).values()) for c in chambers_data])
    
    total_capacity = sum([c.get("capacity_pallets", 0) for c in chambers_data])
    total_occupied = sum([c.get("occupied_pallets", 0) for c in chambers_data])
    
    all_cats = set()
    for c in chambers_data:
        all_cats.update(c.get("stock_data", {}).keys())
    total_categories = len(all_cats)
    
    occupancy_pct = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
    
    st.markdown(f"""
    <div class="stock-kpi-container">
        <div class="stock-kpi-card">
            <div class="stock-kpi-icon">🏭</div>
            <div class="stock-kpi-value">{total_chambers}</div>
            <div class="stock-kpi-label">Ubicaciones</div>
        </div>
        <div class="stock-kpi-card">
            <div class="stock-kpi-icon">📦</div>
            <div class="stock-kpi-value">{total_occupied:,}</div>
            <div class="stock-kpi-label">Pallets Ocupados</div>
        </div>
        <div class="stock-kpi-card">
            <div class="stock-kpi-icon">📊</div>
            <div class="stock-kpi-value">{occupancy_pct:.1f}%</div>
            <div class="stock-kpi-label">Ocupación</div>
        </div>
        <div class="stock-kpi-card">
            <div class="stock-kpi-icon">⚖️</div>
            <div class="stock-kpi-value">{total_kg:,.0f}</div>
            <div class="stock-kpi-label">KG Totales</div>
        </div>
        <div class="stock-kpi-card">
            <div class="stock-kpi-icon">🏷️</div>
            <div class="stock-kpi-value">{total_categories}</div>
            <div class="stock-kpi-label">Categorías</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chamber_indicators(chambers: list):
    """Renderiza indicadores de capacidad arriba del gráfico"""
    cols = st.columns(min(len(chambers), 6))
    
    for i, c in enumerate(chambers[:6]):
        capacity = c.get("capacity_pallets", 0)
        occupied = c.get("occupied_pallets", 0)
        pct = (occupied / capacity * 100) if capacity > 0 else 0
        
        # Color según ocupación
        if pct < 50:
            fill_color = "#00cc66"
        elif pct < 80:
            fill_color = "#ffaa00"
        else:
            fill_color = "#ff6b6b"
        
        with cols[i % 6]:
            st.markdown(f"""
            <div class="chamber-indicator">
                <div class="chamber-indicator-name" title="{c['name']}">{c['name'][:15]}</div>
                <div class="chamber-indicator-stats">{occupied}/{capacity} pallets</div>
                <div class="chamber-indicator-bar">
                    <div class="chamber-indicator-fill" style="width: {min(pct, 100)}%; background: {fill_color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_stock_chart(chambers: list, all_categories: list, category_colors: dict):
    """Renderiza gráfico de barras apiladas de alta calidad"""
    if not chambers:
        return None
    
    chamber_names = [c["name"] for c in chambers]
    
    fig = go.Figure()
    
    # Barras apiladas por categoría
    for cat in all_categories:
        y_values = [c["stock_data"].get(cat, 0) for c in chambers]
        color = category_colors.get(cat, "#888888")
        
        fig.add_trace(go.Bar(
            x=chamber_names,
            y=y_values,
            name=cat,
            marker=dict(
                color=color,
                line=dict(color='rgba(255,255,255,0.3)', width=0.5)
            ),
            hovertemplate=(
                f'<b>{cat}</b><br>'
                'Cámara: %{x}<br>'
                'Stock: %{y:,.0f} kg<extra></extra>'
            )
        ))

    fig.update_layout(
        height=500,
        barmode='stack',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 11},
        xaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.05)",
            tickangle=-45,
            tickfont=dict(size=10, color="#ccc"),
            showline=True,
            linecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            title="Stock (kg)",
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=10),
            tickformat=",",
            showline=True,
            linecolor="rgba(255,255,255,0.2)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=9),
            itemsizing="constant"
        ),
        margin=dict(l=70, r=20, t=80, b=120),
        hoverlabel=dict(
            bgcolor="rgba(20,20,30,0.95)",
            bordercolor="rgba(255,255,255,0.3)",
            font=dict(size=12)
        ),
        bargap=0.15,
        bargroupgap=0.1
    )
    
    return fig


def render_lots_list(lots: list, category: str):
    """Renderiza lista dinámica de lotes con colores por antigüedad"""
    if not lots:
        st.info(f"No hay lotes para la categoría: {category}")
        return
    
    # Resumen
    total_kg = sum(l["quantity"] for l in lots)
    total_pallets = sum(l["pallets"] for l in lots)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔢 Lotes", len(lots))
    with col2:
        st.metric("📦 Pallets", total_pallets)
    with col3:
        st.metric("⚖️ Total KG", f"{total_kg:,.0f}")
    
    st.markdown("---")
    
    # Lista de lotes
    for lot in lots[:20]:  # Limitar a 20
        age_class, border_color, age_label = get_age_class(lot["days_old"])
        
        locations_str = ", ".join(lot["locations"][:2])
        if len(lot["locations"]) > 2:
            locations_str += f" +{len(lot['locations'])-2}"
        
        st.markdown(f"""
        <div class="lot-item" style="border-left-color: {border_color};">
            <div class="lot-info">
                <div class="lot-name">📋 {lot['lot']}</div>
                <div class="lot-product">{lot['product'][:40]}...</div>
                <div class="lot-product">📍 {locations_str}</div>
            </div>
            <div class="lot-stats">
                <div class="lot-qty">{lot['quantity']:,.0f} kg</div>
                <div class="lot-date {age_class}">{lot['in_date']} ({age_label})</div>
                <div class="lot-pallets">{lot['pallets']} pallets</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if len(lots) > 20:
        st.caption(f"... y {len(lots) - 20} lotes más")


def render_pallets_table(pallets: list):
    """Renderiza tabla de pallets con colores por antigüedad"""
    if not pallets:
        st.info("No hay pallets para mostrar en esta ubicación.")
        return
    
    df = pd.DataFrame(pallets)
    
    # Calcular totales
    total_kg = df["quantity"].sum()
    total_pallets = len(df)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📦 Total Pallets", f"{total_pallets}")
    with col2:
        st.metric("⚖️ Total Kilos", f"{total_kg:,.2f} kg")
    
    # Añadir columna de antigüedad visual
    def age_indicator(days):
        _, color, label = get_age_class(days)
        return f"🟢 {label}" if days < 30 else f"🟡 {label}" if days < 90 else f"🟠 {label}" if days < 180 else f"🔴 {label}"
    
    if "days_old" in df.columns:
        df["Antigüedad"] = df["days_old"].apply(age_indicator)
    
    columns_to_show = ["pallet", "product", "lot", "quantity", "in_date", "Antigüedad"]
    available_cols = [c for c in columns_to_show if c in df.columns]
    
    st.dataframe(
        df[available_cols],
        use_container_width=True,
        height=400,
        column_config={
            "pallet": st.column_config.TextColumn("Pallet", width="medium"),
            "product": st.column_config.TextColumn("Producto", width="large"),
            "lot": st.column_config.TextColumn("Lote", width="medium"),
            "quantity": st.column_config.NumberColumn("Kilos", format="%.2f kg"),
            "in_date": st.column_config.TextColumn("Fecha Entrada", width="small"),
            "Antigüedad": st.column_config.TextColumn("Antigüedad", width="small")
        },
        hide_index=True
    )


def render_stock_dashboard():
    """Renderiza el dashboard de stock"""
    
    # Inyectar CSS
    st.markdown(STOCK_CSS, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown("### 🔍 Filtros de Stock")
    
    if st.sidebar.button("🔄 Recargar Datos", use_container_width=True, type="primary"):
        for key in ["stock_data", "selected_category", "lots_data"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Cargar datos
    if "stock_data" not in st.session_state:
        with st.spinner("🔄 Cargando stock desde Odoo..."):
            st.session_state["stock_data"] = get_stock_data()
    
    chambers_data = st.session_state.get("stock_data", [])
    
    if not chambers_data:
        st.markdown("""
        <div style="text-align: center; padding: 50px; background: rgba(255,255,255,0.05); border-radius: 15px; margin: 20px 0;">
            <div style="font-size: 4rem; margin-bottom: 20px;">📦</div>
            <h3 style="color: #fff;">No hay datos de stock</h3>
            <p style="color: #888;">Haz clic en "Recargar Datos" para obtener el inventario.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # --- KPIs ---
    render_kpis(chambers_data)
    
    # --- Filtros en sidebar ---
    parents = sorted(list(set([c.get("parent_name", "Sin Padre") for c in chambers_data])))
    
    selected_parents = st.sidebar.multiselect(
        "Zona / Ubicación Padre",
        options=parents,
        default=parents,
        key="stock_filter_parents"
    )
    
    filtered_chambers = [c for c in chambers_data if c.get("parent_name", "Sin Padre") in selected_parents]
    chamber_names = sorted([c["name"] for c in filtered_chambers])
    
    selected_chambers = st.sidebar.multiselect(
        "Cámaras Específicas",
        options=chamber_names,
        default=chamber_names,
        key="stock_filter_chambers"
    )
    
    final_chambers = [c for c in filtered_chambers if c["name"] in selected_chambers]
    
    if not final_chambers:
        st.info("Selecciona al menos una cámara para visualizar.")
        return
    
    # Obtener todas las categorías y asignar colores
    all_categories = set()
    for c in final_chambers:
        all_categories.update(c.get("stock_data", {}).keys())
    all_categories = sorted(list(all_categories))
    
    # Mapa de colores por categoría
    category_colors = {cat: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, cat in enumerate(all_categories)}
    
    st.markdown("---")
    
    # --- Indicadores de Capacidad ---
    st.markdown('<div class="section-header"><span class="section-icon">📊</span><span class="section-title">Capacidad por Cámara</span></div>', unsafe_allow_html=True)
    render_chamber_indicators(final_chambers)
    
    # --- Gráfico Principal (más ancho) ---
    st.markdown('<div class="section-header"><span class="section-icon">📈</span><span class="section-title">Stock por Ubicación</span></div>', unsafe_allow_html=True)
    
    fig = render_stock_chart(final_chambers, all_categories, category_colors)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="stock_chart_main")
    
    st.markdown("---")
    
    # --- Selector de Categoría para Lista Dinámica ---
    st.markdown('<div class="section-header"><span class="section-icon">🏷️</span><span class="section-title">Seleccionar Categoría para Ver Lotes</span></div>', unsafe_allow_html=True)
    
    # Crear chips de categorías
    cat_cols = st.columns(min(len(all_categories), 4))
    
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = all_categories[0] if all_categories else None
    
    selected_cat = st.selectbox(
        "Categoría",
        options=all_categories,
        index=all_categories.index(st.session_state["selected_category"]) if st.session_state["selected_category"] in all_categories else 0,
        key="category_selector",
        label_visibility="collapsed"
    )
    
    st.session_state["selected_category"] = selected_cat
    
    # Mostrar color de la categoría seleccionada
    if selected_cat:
        cat_color = category_colors.get(selected_cat, "#888")
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
            <div style="width: 20px; height: 20px; background: {cat_color}; border-radius: 4px;"></div>
            <span style="color: #fff; font-weight: 600;">{selected_cat}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # --- Lista Dinámica de Lotes ---
    col_lots, col_legend = st.columns([3, 1])
    
    with col_lots:
        st.markdown('<div class="section-header"><span class="section-icon">📋</span><span class="section-title">Lotes por Antigüedad</span></div>', unsafe_allow_html=True)
        
        if selected_cat:
            location_ids = [c["id"] for c in final_chambers]
            
            with st.spinner("Cargando lotes..."):
                lots = get_lots_by_category(selected_cat, location_ids)
            
            render_lots_list(lots, selected_cat)
    
    with col_legend:
        st.markdown('<div class="section-header"><span class="section-icon">🎨</span><span class="section-title">Leyenda</span></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="padding: 15px; background: rgba(255,255,255,0.03); border-radius: 10px;">
            <div style="margin: 8px 0; display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background: #00ff88; border-radius: 50%;"></div>
                <span style="color: #00ff88; font-size: 0.85rem;">< 1 mes (Fresco)</span>
            </div>
            <div style="margin: 8px 0; display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background: #88ff00; border-radius: 50%;"></div>
                <span style="color: #88ff00; font-size: 0.85rem;">1-3 meses</span>
            </div>
            <div style="margin: 8px 0; display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background: #ffaa00; border-radius: 50%;"></div>
                <span style="color: #ffaa00; font-size: 0.85rem;">3-6 meses</span>
            </div>
            <div style="margin: 8px 0; display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background: #ff6b6b; border-radius: 50%;"></div>
                <span style="color: #ff6b6b; font-size: 0.85rem;">6-12 meses</span>
            </div>
            <div style="margin: 8px 0; display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background: #ff0000; border-radius: 50%;"></div>
                <span style="color: #ff0000; font-size: 0.85rem;">> 1 año (Crítico)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- Detalle de Pallets (existente) ---
    st.markdown('<div class="section-header"><span class="section-icon">📦</span><span class="section-title">Detalle de Pallets por Cámara</span></div>', unsafe_allow_html=True)
    
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        selected_chamber_name = st.selectbox(
            "Seleccionar Cámara",
            options=[c["name"] for c in final_chambers],
            key="stock_detail_chamber"
        )
    
    with col_sel2:
        selected_chamber = next((c for c in final_chambers if c["name"] == selected_chamber_name), None)
        chamber_categories = ["Todas"] + list(selected_chamber.get("stock_data", {}).keys()) if selected_chamber else ["Todas"]
        
        selected_category = st.selectbox(
            "Filtrar por Categoría",
            options=chamber_categories,
            key="stock_detail_category"
        )
    
    if selected_chamber:
        category_filter = None if selected_category == "Todas" else selected_category
        
        with st.spinner("Cargando pallets..."):
            pallets = get_pallets(selected_chamber["id"], category_filter)
        
        render_pallets_table(pallets)

