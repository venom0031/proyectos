"""
Módulo de gestión de temas - Integra SpA
Aplica estilos visuales profesionales compatibles con el tema nativo de Streamlit.
NO sobrescribe el tema - deja que Streamlit Settings maneje dark/light mode.
"""
import streamlit as st
from typing import Optional, Dict, Any

from db_connection import execute_query, execute_update
from config_manager import get_config, set_config


# ============================================
# COLORES ACCENT (verde corporativo)
# ============================================
ACCENT_COLOR = '#00C853'
ACCENT_HOVER = '#00B548'


# ============================================
# CONFIGURACIÓN DE EMPRESA
# ============================================
def get_empresa_theme_config(empresa_id: int) -> Dict[str, Any]:
    """Obtiene la configuración de tema de una empresa."""
    try:
        result = execute_query(
            "SELECT color_primario, logo_url FROM empresas WHERE id = %s",
            (empresa_id,),
            fetch_one=True
        )
        if result:
            return {
                'color_primario': result.get('color_primario'),
                'logo_url': result.get('logo_url')
            }
    except Exception:
        pass
    return {'color_primario': None, 'logo_url': None}


def set_empresa_theme_config(empresa_id: int, color_primario: str = None, logo_url: str = None) -> bool:
    """Actualiza la configuración de tema de una empresa."""
    try:
        execute_update(
            """
            UPDATE empresas 
            SET color_primario = %s, logo_url = %s
            WHERE id = %s
            """,
            (color_primario, logo_url, empresa_id)
        )
        return True
    except Exception as e:
        print(f"Error actualizando tema de empresa: {e}")
        return False


def get_current_user_empresa_config() -> Dict[str, Any]:
    """Obtiene la config de tema de la primera empresa del usuario actual."""
    if not st.session_state.get('authenticated'):
        return {'color_primario': None, 'logo_url': None}
    
    if st.session_state.get('is_admin'):
        return {'color_primario': None, 'logo_url': None}
    
    empresas = st.session_state.get('empresas', [])
    if empresas and len(empresas) > 0:
        return get_empresa_theme_config(empresas[0]['id'])
    
    return {'color_primario': None, 'logo_url': None}


# ============================================
# CSS VISUAL POLISH (Compatible con tema nativo)
# ============================================
def generate_visual_polish_css(empresa_color: str = None) -> str:
    """
    Genera CSS que mejora la apariencia visual SIN sobrescribir
    los colores del tema nativo de Streamlit.
    Solo agrega: transiciones, bordes redondeados, efectos hover, etc.
    """
    accent = empresa_color if empresa_color else ACCENT_COLOR
    
    css = f"""
    <style>
    /* ========================================
       INTEGRA SPA - VISUAL POLISH
       Compatible con tema nativo de Streamlit
       NO sobrescribe colores de fondo ni texto
    ======================================== */
    
    /* Transiciones suaves globales */
    * {{
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
    }}
    
    /* ========================================
       TABS - Mejorar separación visual
    ======================================== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px !important;
        padding: 4px !important;
        border-radius: 10px !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        margin: 0 2px !important;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        opacity: 0.85;
    }}
    
    .stTabs [aria-selected="true"] {{
        font-weight: 600 !important;
    }}
    
    /* Separación visual de tab panels */
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: 1rem !important;
    }}
    
    /* ========================================
       BOTONES - Estilo premium
    ======================================== */
    .stButton > button[kind="primary"],
    .stButton > button:not([kind]) {{
        background: linear-gradient(135deg, {accent} 0%, {ACCENT_HOVER} 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px {accent}40 !important;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px {accent}50 !important;
    }}
    
    .stButton > button:active {{
        transform: translateY(0) !important;
    }}
    
    /* Download buttons - azul */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px #3B82F640 !important;
    }}
    
    .stDownloadButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px #3B82F650 !important;
    }}
    
    /* ========================================
       INPUTS - Bordes redondeados y focus
    ======================================== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        border-radius: 8px !important;
    }}
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 2px {accent}33 !important;
    }}
    
    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        border-radius: 8px !important;
    }}
    
    /* ========================================
       EXPANDERS - Bordes redondeados
    ======================================== */
    .streamlit-expanderHeader {{
        border-radius: 8px !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        opacity: 0.9;
    }}
    
    /* ========================================
       ALERTAS - Bordes redondeados
    ======================================== */
    .stAlert {{
        border-radius: 8px !important;
    }}
    
    /* ========================================
       FILE UPLOADER - Estilo mejorado
    ======================================== */
    [data-testid="stFileUploader"] {{
        border-radius: 10px !important;
    }}
    
    [data-testid="stFileUploader"]:hover {{
        border-color: {accent} !important;
    }}
    
    /* ========================================
       DATAFRAMES - Bordes redondeados
    ======================================== */
    .stDataFrame {{
        border-radius: 10px !important;
        overflow: hidden !important;
    }}
    
    /* Scrollbar styling */
    .stDataFrame > div > div {{
        scrollbar-width: thin;
        scrollbar-color: {accent}40 transparent;
    }}
    
    .stDataFrame > div > div::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    .stDataFrame > div > div::-webkit-scrollbar-track {{
        background: transparent;
    }}
    
    .stDataFrame > div > div::-webkit-scrollbar-thumb {{
        background-color: {accent}40;
        border-radius: 4px;
    }}
    
    /* ========================================
       SIDEBAR - Efectos sutiles
    ======================================== */
    [data-testid="stSidebar"] .stButton > button:hover {{
        transform: translateY(-1px);
    }}
    
    /* ========================================
       COMPANY LOGO - Contenedor
    ======================================== */
    .company-logo-container {{
        display: flex;
        justify-content: center;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }}
    
    .company-logo-container img {{
        max-width: 150px;
        max-height: 60px;
        object-fit: contain;
        border-radius: 8px;
    }}
    
    </style>
    """
    
    return css


# ============================================
# COMPONENTES DE UI
# ============================================
def apply_visual_polish():
    """
    Aplica estilos visuales profesionales.
    Compatible con el tema nativo de Streamlit (Settings → Theme).
    """
    empresa_config = get_current_user_empresa_config()
    css = generate_visual_polish_css(empresa_color=empresa_config.get('color_primario'))
    st.markdown(css, unsafe_allow_html=True)


def render_company_logo():
    """Renderiza el logo de la empresa si está configurado."""
    empresa_config = get_current_user_empresa_config()
    logo_url = empresa_config.get('logo_url')
    
    if logo_url:
        st.markdown(f"""
        <div class="company-logo-container">
            <img src="{logo_url}" alt="Logo empresa" />
        </div>
        """, unsafe_allow_html=True)


# ============================================
# FUNCIONES LEGACY (para compatibilidad)
# ============================================
THEMES = {
    'light': {'name': 'Claro', 'icon': '☀️'},
    'dark': {'name': 'Oscuro', 'icon': '🌙'}
}

def get_default_theme() -> str:
    """Legacy: Obtiene el tema por defecto."""
    return 'light'

def set_default_theme(theme: str, user_id: int = None) -> bool:
    """Legacy: Ya no usado - Streamlit maneja el tema."""
    return True
