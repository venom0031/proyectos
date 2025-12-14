# ============================================
# MÓDULO DE AUTENTICACIÓN
# Maneja login, validación de usuarios y sesión
# ============================================
import bcrypt
import streamlit as st
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from db_connection import execute_query
from config import APP_CONFIG

logger = logging.getLogger(__name__)


# ============================================
# SEGURIDAD: Rate Limiting para Login
# ============================================
def check_login_attempts(username: str) -> bool:
    """
    Verifica si el usuario puede intentar login.
    Bloquea por 5 minutos después de 5 intentos fallidos.
    """
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    attempts = st.session_state.login_attempts.get(username, {'count': 0, 'blocked_until': None})
    
    if attempts.get('blocked_until') and datetime.now() < attempts['blocked_until']:
        remaining = int((attempts['blocked_until'] - datetime.now()).total_seconds())
        st.error(f"⏳ Demasiados intentos fallidos. Espera {remaining} segundos.")
        logger.warning(f"Login bloqueado para {username}: {remaining}s restantes")
        return False
    
    return True


def record_failed_login(username: str):
    """Registra un intento de login fallido."""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    attempts = st.session_state.login_attempts.get(username, {'count': 0, 'blocked_until': None})
    attempts['count'] = attempts.get('count', 0) + 1
    
    if attempts['count'] >= 5:
        attempts['blocked_until'] = datetime.now() + timedelta(minutes=5)
        attempts['count'] = 0
        logger.warning(f"Usuario {username} bloqueado por 5 minutos tras 5 intentos fallidos")
    
    st.session_state.login_attempts[username] = attempts


def clear_login_attempts(username: str):
    """Limpia los intentos de login tras un login exitoso."""
    if 'login_attempts' in st.session_state and username in st.session_state.login_attempts:
        del st.session_state.login_attempts[username]


# ============================================
# SEGURIDAD: Session Timeout
# ============================================
def check_session_timeout() -> bool:
    """
    Verifica si la sesión ha expirado por inactividad.
    Retorna False si la sesión expiró (usuario debe re-autenticarse).
    """
    if not st.session_state.get('authenticated', False):
        return True  # No hay sesión activa, no aplica timeout
    
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
        return True
    
    timeout_minutes = APP_CONFIG.get('session_timeout_minutes', 60)
    elapsed = datetime.now() - st.session_state.last_activity
    
    if elapsed > timedelta(minutes=timeout_minutes):
        username = st.session_state.get('username', 'Unknown')
        logger.info(f"Sesión expirada por inactividad: {username}")
        logout_user()
        st.warning("⏰ Tu sesión ha expirado por inactividad. Por favor, inicia sesión nuevamente.")
        return False
    
    # Actualizar última actividad
    st.session_state.last_activity = datetime.now()
    return True


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
    st.session_state.last_activity = datetime.now()  # Iniciar tracking de actividad
    
    if not user_data['is_admin']:
        st.session_state.empresas = get_user_companies(user_data['id'])
    else:
        st.session_state.empresas = []
    
    # Limpiar intentos fallidos tras login exitoso
    clear_login_attempts(user_data['username'])
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
    """
    Verifica que el usuario esté autenticado y que la sesión no haya expirado.
    Incluye verificación de timeout de sesión.
    """
    init_session_state()
    
    # Verificar timeout de sesión
    if not check_session_timeout():
        show_login_form()
        return False
    
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
                    # Verificar rate limiting antes de intentar autenticación
                    if not check_login_attempts(username):
                        pass  # El mensaje de error ya se muestra en check_login_attempts
                    else:
                        user_data = authenticate(username, password)
                        
                        if user_data:
                            login_user(user_data)
                            st.success(f"¡Bienvenido, {user_data['nombre_completo']}!")
                            st.rerun()
                        else:
                            record_failed_login(username)
                            attempts_info = st.session_state.login_attempts.get(username, {})
                            remaining = 5 - attempts_info.get('count', 0)
                            if remaining > 0:
                                st.error(f"Usuario o contraseña incorrectos. Intentos restantes: {remaining}")
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
    """Muestra información del usuario en el sidebar con estilos mejorados."""
    if st.session_state.authenticated:
        # Importar y aplicar estilos visuales (sin toggle de tema - usa Streamlit nativo)
        from theme_manager import apply_visual_polish, render_company_logo
        
        # Aplicar estilos visuales profesionales (compatibles con tema nativo)
        apply_visual_polish()
        
        with st.sidebar:
            # Company logo if available
            render_company_logo()
            
            st.markdown("---")
            st.markdown(f"**👤 Usuario:** {st.session_state.nombre_completo}")
            st.markdown(f"**🔑 Login:** {st.session_state.username}")
            
            if st.session_state.is_admin:
                st.markdown("**🛡️ Rol:** Administrador")
            else:
                # Mostrar establecimientos en vez de empresas
                empresa_ids = [e['id'] for e in st.session_state.empresas] if st.session_state.empresas else []
                
                if empresa_ids:
                    from db_connection import execute_query
                    # Obtener establecimientos de las empresas del usuario
                    establecimientos = execute_query(
                        """
                        SELECT est.nombre, emp.nombre as empresa
                        FROM establecimientos est
                        JOIN empresas emp ON est.empresa_id = emp.id
                        WHERE est.empresa_id IN ({})
                        ORDER BY est.nombre
                        """.format(','.join(['%s'] * len(empresa_ids))),
                        tuple(empresa_ids),
                        fetch_all=True
                    )
                    
                    if establecimientos:
                        st.markdown(f"**📍 Establecimientos:** {len(establecimientos)}")
                        for est in establecimientos:
                            st.markdown(f"  • {est['nombre']}")
                    else:
                        st.markdown("**📍 Establecimientos:** 0")
                else:
                    st.markdown("**📍 Establecimientos:** 0")
            
            st.markdown("---")
            
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                logout_user()
                st.rerun()
