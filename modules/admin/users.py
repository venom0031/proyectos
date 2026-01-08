# =====================================================
# MÓDULO: Gestión de Usuarios
# =====================================================
"""
Funciones para renderizar la gestión de usuarios en el admin panel.
"""

import streamlit as st
import pandas as pd
import bcrypt

from db_connection import execute_query, execute_update


def render_users_tab():
    """Renderiza la pestaña completa de gestión de usuarios."""
    st.header("👥 Gestión de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["Lista de Usuarios", "Crear Usuario", "🔑 Cambiar Contraseña"])
    
    with tab1:
        _render_users_list()
    
    with tab2:
        _render_create_user_form()
    
    with tab3:
        _render_change_password_form()


def _render_users_list():
    """Muestra la lista de usuarios con sus empresas asignadas."""
    usuarios = execute_query("""
        SELECT u.id, u.username, u.nombre_completo, u.email, u.is_admin, u.activo,
               STRING_AGG(e.nombre, ', ') as empresas
        FROM usuarios u
        LEFT JOIN usuario_empresa ue ON u.id = ue.usuario_id
        LEFT JOIN empresas e ON ue.empresa_id = e.id
        GROUP BY u.id, u.username, u.nombre_completo, u.email, u.is_admin, u.activo
        ORDER BY u.id
    """)
    
    if usuarios:
        df_usuarios = pd.DataFrame(usuarios)
        df_usuarios['Admin'] = df_usuarios['is_admin'].map({True: '✅', False: '❌'})
        df_usuarios['Activo'] = df_usuarios['activo'].map({True: '✅', False: '❌'})
        
        st.dataframe(
            df_usuarios[['id', 'username', 'nombre_completo', 'email', 'Admin', 'Activo', 'empresas']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay usuarios registrados")


def _render_create_user_form():
    """Formulario para crear un nuevo usuario."""
    st.subheader("Crear Nuevo Usuario")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username*")
            new_nombre = st.text_input("Nombre Completo*")
            new_password = st.text_input("Contraseña*", type="password")
        
        with col2:
            new_email = st.text_input("Email")
            new_is_admin = st.checkbox("¿Es administrador?")
            
            # Seleccionar empresas
            empresas = execute_query("SELECT id, nombre FROM empresas ORDER BY nombre")
            empresas_options = {e['id']: e['nombre'] for e in empresas} if empresas else {}
            
            selected_empresas = st.multiselect(
                "Empresas asignadas*",
                options=list(empresas_options.keys()),
                format_func=lambda x: empresas_options[x]
            )
        
        submitted = st.form_submit_button("Crear Usuario", type="primary", use_container_width=True)
        
        if submitted:
            if not new_username or not new_nombre or not new_password:
                st.error("❌ Completar campos obligatorios")
            elif not selected_empresas and not new_is_admin:
                st.error("❌ Debe asignar al menos una empresa (o marcar como admin)")
            else:
                try:
                    # Hash password
                    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Insert user
                    user_id = execute_query(
                        """INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo)
                           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                        (new_username, password_hash, new_nombre, new_email, new_is_admin, True),
                        fetch_one=True
                    )['id']
                    
                    # Assign companies
                    for empresa_id in selected_empresas:
                        execute_update(
                            "INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES (%s, %s)",
                            (user_id, empresa_id)
                        )
                    
                    st.success(f"✅ Usuario '{new_username}' creado exitosamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al crear usuario: {e}")


def _render_change_password_form():
    """Formulario para cambiar contraseña de un usuario."""
    st.subheader("🔑 Cambiar Contraseña de Usuario")
    
    st.info("""
    **Requisitos de contraseña:**
    - Mínimo 8 caracteres
    - Se recomienda usar mayúsculas, minúsculas, números y símbolos
    """)
    
    # Obtener lista de usuarios
    usuarios_pwd = execute_query("""
        SELECT id, username, nombre_completo 
        FROM usuarios 
        WHERE activo = true
        ORDER BY nombre_completo
    """)
    
    if usuarios_pwd:
        user_options = {u['id']: f"{u['nombre_completo']} ({u['username']})" for u in usuarios_pwd}
        
        with st.form("change_password_form"):
            selected_user_id = st.selectbox(
                "Seleccionar usuario:",
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x]
            )
            
            new_password_1 = st.text_input("Nueva contraseña:", type="password")
            new_password_2 = st.text_input("Confirmar contraseña:", type="password")
            
            submitted_pwd = st.form_submit_button("Cambiar Contraseña", type="primary", use_container_width=True)
            
            if submitted_pwd:
                if not new_password_1 or not new_password_2:
                    st.error("❌ Complete ambos campos de contraseña")
                elif new_password_1 != new_password_2:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(new_password_1) < 8:
                    st.error("❌ La contraseña debe tener al menos 8 caracteres")
                else:
                    try:
                        # Hash new password
                        new_hash = bcrypt.hashpw(new_password_1.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        # Update in database
                        execute_update(
                            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                            (new_hash, selected_user_id)
                        )
                        
                        # Get username for log
                        user_info = next((u for u in usuarios_pwd if u['id'] == selected_user_id), None)
                        if user_info:
                            st.success(f"✅ Contraseña cambiada exitosamente para {user_info['nombre_completo']}")
                        else:
                            st.success("✅ Contraseña cambiada exitosamente")
                        
                    except Exception as e:
                        st.error(f"❌ Error al cambiar contraseña: {e}")
    else:
        st.warning("No hay usuarios activos")
