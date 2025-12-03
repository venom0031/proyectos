# ============================================
# MÓDULO DE AUTENTICACIÓN
# Maneja login, validación de usuarios y sesión
# ============================================
import bcrypt
import streamlit as st
from typing import Optional, Dict, Any, List
import logging

from db_connection import execute_query

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Genera hash bcrypt de una contraseña."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica si una contraseña coincide con su hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error al verificar password: {e}")
        return False


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Autentica un usuario contra la base de datos."""
    try:
        query = """
            SELECT id, username, password_hash, nombre_completo, email, is_admin, activo
            FROM usuarios
            WHERE username = %s AND activo = true
        """
        
        user = execute_query(query, params=(username,), fetch_one=True, return_dict=True)
        
        if not user:
            logger.warning(f"Usuario no encontrado o inactivo: {username}")
            return None
        
        if verify_password(password, user['password_hash']):
            logger.info(f"Autenticación exitosa: {username}")
            return {
                'id': user['id'],
                'username': user['username'],
                'nombre_completo': user['nombre_completo'],
                'email': user['email'],
                'is_admin': user['is_admin'],
                'activo': user['activo']
            }
        else:
            logger.warning(f"Contraseña incorrecta para usuario: {username}")
            return None
            
    except Exception as e:
        logger.error(f"Error en autenticación: {e}")
        return None


def get_user_companies(user_id: int) -> List[Dict[str, Any]]:
    """Obtiene las empresas asociadas a un usuario."""
    try:
        query = """
            SELECT e.id, e.nombre, e.codigo
            FROM empresas e
            JOIN usuario_empresa ue ON e.id = ue.empresa_id
            WHERE ue.usuario_id = %s
            ORDER BY e.nombre
        """
        
        companies = execute_query(query, params=(user_id,), fetch_all=True, return_dict=True)
        return companies or []
        
    except Exception as e:
        logger.error(f"Error al obtener empresas del usuario: {e}")
        return []


def init_session_state():
    """Inicializa el estado de sesión de Streamlit."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'nombre_completo' not in st.session_state:
        st.session_state.nombre_completo = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'empresas' not in st.session_state:
        st.session_state.empresas = []


def login_user(user_data: Dict[str, Any]):
    """Guarda los datos del usuario en la sesión."""
    st.session_state.authenticated = True
    st.session_state.user_id = user_data['id']
    st.session_state.username = user_data['username']
    st.session_state.nombre_completo = user_data['nombre_completo']
    st.session_state.is_admin = user_data['is_admin']
    
    if not user_data['is_admin']:
        st.session_state.empresas = get_user_companies(user_data['id'])
    else:
        st.session_state.empresas = []
    
    logger.info(f"Usuario logueado: {user_data['username']}")


def logout_user():
    """Cierra la sesión del usuario actual."""
    username = st.session_state.get('username', 'Unknown')
    
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    init_session_state()
    logger.info(f"Usuario deslogueado: {username}")


# Alias para compatibilidad
logout = logout_user


def require_auth() -> bool:
    """Verifica que el usuario esté autenticado."""
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login_form()
        return False
    
    return True


def show_login_form():
    """Muestra el formulario de login."""
    st.title("🔐 Iniciar Sesión - Integra SpA")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Ingrese sus credenciales")
            
            username = st.text_input("Usuario", key="login_username")
            password = st.text_input("Contraseña", type="password", key="login_password")
            
            submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Por favor ingrese usuario y contraseña")
                else:
                    user_data = authenticate(username, password)
                    
                    if user_data:
                        login_user(user_data)
                        st.success(f"¡Bienvenido, {user_data['nombre_completo']}!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
        
        with st.expander("ℹ️ Usuarios de prueba"):
            st.markdown("""
            **Usuarios disponibles:**
            - `admin` / `admin123` (administrador)
            - `user_eduvigis` / `test123`
            - `user_lagos` / `test123`
            """)


def show_user_info():
    """Muestra información del usuario en el sidebar."""
    if st.session_state.authenticated:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**👤 Usuario:** {st.session_state.nombre_completo}")
            st.markdown(f"**🔑 Login:** {st.session_state.username}")
            
            if st.session_state.is_admin:
                st.markdown("**🛡️ Rol:** Administrador")
            else:
                st.markdown(f"**🏢 Empresas:** {len(st.session_state.empresas)}")
                if st.session_state.empresas:
                    for company in st.session_state.empresas:
                        st.markdown(f"  - {company['nombre']}")
            
            st.markdown("---")
            
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                logout_user()
                st.rerun()
