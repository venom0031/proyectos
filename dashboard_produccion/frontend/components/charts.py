"""
Componentes de visualización con Plotly
"""
import streamlit as st
import plotly.graph_objects as go


def render_rendimiento_gauge(kpis: dict):
    """
    Renderiza el gráfico de rendimiento como gauge
    
    Args:
        kpis: Diccionario con KPIs calculados
    """
    st.subheader("📈 Rendimiento del Proceso")
    
    rendimiento = kpis.get("rendimiento_real_%", 0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
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
    
    fig.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"}
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_custom_chart(title: str, data: dict, chart_type: str = "bar"):
    """
    Renderiza un gráfico personalizable
    
    Args:
        title: Título del gráfico
        data: Datos para el gráfico (dict con x, y)
        chart_type: Tipo de gráfico ('bar', 'line', 'pie')
    """
    st.subheader(title)
    
    fig = go.Figure()
    
    if chart_type == "bar":
        fig.add_trace(go.Bar(
            x=data.get("x", []),
            y=data.get("y", []),
            marker_color="#00cc66"
        ))
    elif chart_type == "line":
        fig.add_trace(go.Scatter(
            x=data.get("x", []),
            y=data.get("y", []),
            mode="lines+markers",
            line={"color": "#00cc66", "width": 2}
        ))
    elif chart_type == "pie":
        fig.add_trace(go.Pie(
            labels=data.get("labels", []),
            values=data.get("values", []),
            marker={"colors": ["#00cc66", "#00ff88", "#ffaa00", "#ff4444"]}
        ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis={"gridcolor": "#333"},
        yaxis={"gridcolor": "#333"}
    )
    
    st.plotly_chart(fig, use_container_width=True)
