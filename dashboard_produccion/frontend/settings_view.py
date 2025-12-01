"""
Vista de Configuración del Sistema
Permite configurar la conexión a Odoo desde la interfaz web
"""
import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
SETTINGS_TOKEN = os.getenv("SETTINGS_TOKEN")

# ==============================
#  ESTILOS CSS
# ==============================
SETTINGS_CSS = """
<style>
    .settings-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 16px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .settings-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #fff;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-connected {
        background: rgba(0, 204, 102, 0.2);
        color: #00cc66;
        border: 1px solid #00cc66;
    }
    
    .status-disconnected {
        background: rgba(255, 107, 107, 0.2);
        color: #ff6b6b;
        border: 1px solid #ff6b6b;
    }
    
    .info-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #00cc66;
    }
    
    .warning-box {
        background: rgba(255, 170, 0, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #ffaa00;
    }
</style>
"""


def _auth_headers():
    """Headers para proteger llamadas de configuraci�n."""
    return {"X-Settings-Token": SETTINGS_TOKEN} if SETTINGS_TOKEN else {}


def get_connection_status():
    """Obtiene el estado de conexión actual"""
    try:
        response = requests.get(
            f"{API_URL}/settings/status",
            timeout=5,
            headers=_auth_headers()
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"connected": False, "message": "No se pudo conectar al backend"}


def get_current_config():
    """Obtiene la configuración actual"""
    try:
        response = requests.get(
            f"{API_URL}/settings/odoo",
            timeout=5,
            headers=_auth_headers()
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}


def test_connection(url, db, user, password):
    """Prueba la conexión con las credenciales proporcionadas"""
    try:
        response = requests.post(
            f"{API_URL}/settings/test-connection",
            json={
                "odoo_url": url,
                "odoo_db": db,
                "odoo_user": user,
                "odoo_password": password
            },
            timeout=30,
            headers=_auth_headers()
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": False, "message": "Error desconocido"}


def save_config(url, db, user, password):
    """Guarda la configuración"""
    try:
        response = requests.post(
            f"{API_URL}/settings/odoo",
            json={
                "odoo_url": url,
                "odoo_db": db,
                "odoo_user": user,
                "odoo_password": password
            },
            timeout=10,
            headers=_auth_headers()
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": False, "message": "Error al guardar"}


def render_settings_view():
    """Renderiza la vista de configuración"""
    
    # Inyectar CSS
    st.markdown(SETTINGS_CSS, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #fff; margin: 0;">⚙️ Configuración del Sistema</h1>
        <p style="color: #888; margin-top: 10px;">Configura la conexión a Odoo</p>
    </div>
    """, unsafe_allow_html=True)

    if not SETTINGS_TOKEN:
        st.warning("Configura la variable SETTINGS_TOKEN en el servidor para usar esta vista.")
        return
    
    # Estado de conexión actual
    status = get_connection_status()
    
    if status.get("connected"):
        st.markdown(f"""
        <div class="status-badge status-connected">
            ✅ Conectado a Odoo | Usuario: {status.get('user', 'N/A')} | DB: {status.get('db', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-badge status-disconnected">
            ❌ Desconectado | {status.get('message', 'Sin conexión')}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Cargar configuración actual
    current_config = get_current_config()
    
    # Formulario de configuración
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">🔗 Conexión Odoo</div>', unsafe_allow_html=True)
        
        # Campos del formulario
        odoo_url = st.text_input(
            "URL de Odoo",
            value=current_config.get("odoo_url", ""),
            placeholder="https://tu-instancia.odoo.com",
            help="URL completa de tu instancia de Odoo"
        )
        
        odoo_db = st.text_input(
            "Base de Datos",
            value=current_config.get("odoo_db", ""),
            placeholder="nombre-base-datos",
            help="Nombre de la base de datos de Odoo"
        )
        
        odoo_user = st.text_input(
            "Usuario",
            value=current_config.get("odoo_user", ""),
            placeholder="usuario@email.com",
            help="Email o usuario de Odoo"
        )
        
        # Password - mostrar placeholder si ya existe
        password_placeholder = "••••••••" if current_config.get("has_password") else ""
        odoo_password = st.text_input(
            "API Key / Contraseña",
            type="password",
            placeholder=password_placeholder or "Tu API Key o contraseña",
            help="API Key de Odoo (recomendado) o contraseña"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            test_btn = st.button("🔍 Probar Conexión", use_container_width=True)
        
        with col_btn2:
            save_btn = st.button("💾 Guardar", use_container_width=True, type="primary")
        
        with col_btn3:
            clear_btn = st.button("🗑️ Limpiar", use_container_width=True)
        
        # Lógica de botones
        if test_btn:
            if not all([odoo_url, odoo_db, odoo_user, odoo_password]):
                st.error("⚠️ Completa todos los campos antes de probar")
            else:
                with st.spinner("Probando conexión..."):
                    result = test_connection(odoo_url, odoo_db, odoo_user, odoo_password)
                
                if result.get("success"):
                    st.success(f"✅ {result.get('message')}")
                    if result.get("version"):
                        st.info(f"📦 Versión de Odoo: {result.get('version')}")
                else:
                    st.error(f"❌ {result.get('message')}")
        
        if save_btn:
            if not all([odoo_url, odoo_db, odoo_user]):
                st.error("⚠️ URL, Base de Datos y Usuario son requeridos")
            elif not odoo_password and not current_config.get("has_password"):
                st.error("⚠️ Ingresa la contraseña o API Key")
            else:
                # Si no se ingresó nueva contraseña, mantener la actual
                password_to_save = odoo_password if odoo_password else None
                
                if password_to_save:
                    with st.spinner("Guardando configuración..."):
                        result = save_config(odoo_url, odoo_db, odoo_user, password_to_save)
                    
                    if result.get("success"):
                        st.success("✅ Configuración guardada correctamente")
                        st.info("🔄 Los cambios se aplicarán inmediatamente")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message')}")
                else:
                    st.warning("⚠️ Ingresa la contraseña para guardar cambios")
        
        if clear_btn:
            st.rerun()
    
    with col2:
        # Panel de ayuda
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">💡 Ayuda</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
            <strong>API Key (Recomendado)</strong><br>
            <small>En Odoo: Preferencias → Cuenta → Claves API → Nueva</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ Seguridad</strong><br>
            <small>Las credenciales se guardan en el servidor. No compartas el acceso.</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Info del sistema
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">📊 Sistema</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        - **API Backend:** `{API_URL}`
        - **Versión:** 2.0.0
        """)
        
        st.markdown("</div>", unsafe_allow_html=True)
