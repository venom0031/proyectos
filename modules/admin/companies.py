# =====================================================
# MÓDULO: Gestión de Empresas y Establecimientos
# =====================================================
"""
Funciones para gestionar empresas y establecimientos en el admin panel.
"""

import streamlit as st
import pandas as pd

from db_connection import execute_query, execute_update


def render_companies_tab():
    """Renderiza la pestaña completa de gestión de empresas."""
    st.header("🏢 Gestión de Empresas")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Lista de Empresas", 
        "Crear Empresa", 
        "Editar Empresa", 
        "📍 Establecimientos"
    ])
    
    with tab1:
        _render_companies_list()
    
    with tab2:
        _render_create_company_form()
    
    with tab3:
        _render_edit_company_form()
    
    with tab4:
        _render_establishments_tab()


def _render_companies_list():
    """Lista de empresas con estadísticas."""
    empresas = execute_query("""
        SELECT e.id, e.codigo, e.nombre,
               COUNT(DISTINCT est.id) as num_establecimientos,
               COUNT(DISTINCT ue.usuario_id) as num_usuarios
        FROM empresas e
        LEFT JOIN establecimientos est ON e.id = est.empresa_id
        LEFT JOIN usuario_empresa ue ON e.id = ue.empresa_id
        GROUP BY e.id, e.codigo, e.nombre
        ORDER BY e.nombre
    """)
    
    if empresas:
        df_empresas = pd.DataFrame(empresas)
        st.dataframe(df_empresas, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Acciones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            empresa_ids = {f"{e['nombre']} ({e['codigo']})": e['id'] for e in empresas}
            selected_empresa = st.selectbox(
                "Seleccionar empresa:",
                options=list(empresa_ids.keys())
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Eliminar Empresa", type="secondary"):
                empresa_id = empresa_ids[selected_empresa]
                try:
                    # Eliminar datos relacionados en cascada
                    execute_update("DELETE FROM datos_semanales WHERE empresa_id = %s", (empresa_id,))
                    execute_update("DELETE FROM datos_diarios WHERE empresa_id = %s", (empresa_id,))
                    execute_update("DELETE FROM historico_mdat WHERE empresa_id = %s", (empresa_id,))
                    execute_update("DELETE FROM establecimientos WHERE empresa_id = %s", (empresa_id,))
                    execute_update("DELETE FROM usuario_empresa WHERE empresa_id = %s", (empresa_id,))
                    execute_update("DELETE FROM empresas WHERE id = %s", (empresa_id,))
                    st.success("✅ Empresa eliminada con todos sus datos asociados")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar en cascada: {e}")
    else:
        st.info("No hay empresas registradas")


def _render_create_company_form():
    """Formulario para crear nueva empresa."""
    st.subheader("Crear Nueva Empresa")
    
    with st.form("create_empresa_form"):
        empresa_codigo = st.text_input("Código (RUT)*", placeholder="96.719.960-5")
        empresa_nombre = st.text_input("Nombre*", placeholder="Eduvigis")
        
        submitted = st.form_submit_button("Crear Empresa", type="primary", use_container_width=True)
        
        if submitted:
            if not empresa_codigo or not empresa_nombre:
                st.error("❌ Completar todos los campos")
            else:
                try:
                    execute_update(
                        "INSERT INTO empresas (codigo, nombre) VALUES (%s, %s)",
                        (empresa_codigo, empresa_nombre)
                    )
                    st.success(f"✅ Empresa '{empresa_nombre}' creada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")


def _render_edit_company_form():
    """Formulario para editar empresa existente."""
    st.subheader("Editar Empresa")
    
    empresas_edit = execute_query(
        "SELECT id, codigo, nombre, color_primario, logo_url FROM empresas ORDER BY nombre"
    )
    
    if empresas_edit:
        empresa_dict = {f"{e['nombre']} ({e['codigo']})": e for e in empresas_edit}
        selected_edit = st.selectbox(
            "Seleccionar empresa a editar:",
            options=list(empresa_dict.keys()),
            key="edit_empresa_select"
        )
        
        empresa_data = empresa_dict[selected_edit]
        
        with st.form("edit_empresa_form"):
            st.write(f"**ID:** {empresa_data['id']}")
            
            new_codigo = st.text_input("Código (RUT)", value=empresa_data['codigo'])
            new_nombre = st.text_input("Nombre", value=empresa_data['nombre'])
            
            st.divider()
            st.markdown("##### 🎨 Personalización Visual")
            
            current_color = empresa_data.get('color_primario') or '#00C853'
            new_color = st.color_picker(
                "Color primario de la empresa",
                value=current_color,
                help="Este color se usará como acento en la interfaz para usuarios de esta empresa"
            )
            
            current_logo = empresa_data.get('logo_url') or ''
            new_logo = st.text_input(
                "URL del logo de la empresa",
                value=current_logo,
                placeholder="https://ejemplo.com/logo.png",
                help="URL de la imagen del logo (formato PNG o JPG recomendado)"
            )
            
            if new_logo:
                st.image(new_logo, caption="Vista previa del logo", width=150)
            
            submitted_edit = st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True)
            
            if submitted_edit:
                if not new_codigo or not new_nombre:
                    st.error("❌ Código y nombre son obligatorios")
                else:
                    try:
                        color_to_save = new_color if new_color != '#00C853' else None
                        logo_to_save = new_logo if new_logo.strip() else None
                        
                        execute_update(
                            "UPDATE empresas SET codigo = %s, nombre = %s, color_primario = %s, logo_url = %s WHERE id = %s",
                            (new_codigo, new_nombre, color_to_save, logo_to_save, empresa_data['id'])
                        )
                        st.success("✅ Empresa actualizada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    else:
        st.info("No hay empresas para editar")


def _render_establishments_tab():
    """Gestión de establecimientos por empresa."""
    st.subheader("📍 Gestión de Establecimientos")
    
    st.info("""
    **¿Cómo se crean los establecimientos?**
    - Los establecimientos se crean **automáticamente** cuando subes un reporte semanal
    - El sistema asocia cada establecimiento del Excel a la empresa indicada en el archivo
    - Aquí puedes ver, editar y reorganizar los establecimientos existentes
    """)
    
    empresas_est = execute_query("SELECT id, codigo, nombre FROM empresas ORDER BY nombre")
    
    if not empresas_est:
        st.warning("No hay empresas registradas. Crea una empresa primero.")
        return
    
    empresa_select_dict = {f"{e['nombre']} ({e['codigo']})": e for e in empresas_est}
    selected_empresa_est = st.selectbox(
        "Seleccionar empresa:",
        options=list(empresa_select_dict.keys()),
        key="est_empresa_select"
    )
    
    empresa_data_est = empresa_select_dict[selected_empresa_est]
    
    # Obtener establecimientos
    establecimientos_empresa = execute_query(
        """
        SELECT est.id, est.nombre, est.superficie_praderas,
               COUNT(DISTINCT ds.id) as registros_semanales,
               COUNT(DISTINCT dd.id) as registros_diarios
        FROM establecimientos est
        LEFT JOIN datos_semanales ds ON est.id = ds.establecimiento_id
        LEFT JOIN datos_diarios dd ON est.id = dd.establecimiento_id
        WHERE est.empresa_id = %s
        GROUP BY est.id, est.nombre, est.superficie_praderas
        ORDER BY est.nombre
        """,
        (empresa_data_est['id'],)
    )
    
    st.divider()
    st.subheader(f"Establecimientos de {empresa_data_est['nombre']}")
    
    if establecimientos_empresa:
        df_est = pd.DataFrame(establecimientos_empresa)
        df_est.columns = ['ID', 'Nombre', 'Superficie (ha)', 'Reg. Semanales', 'Reg. Diarios']
        st.dataframe(df_est, use_container_width=True, hide_index=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        # Eliminar establecimiento
        with col1:
            st.markdown("##### 🗑️ Eliminar Establecimiento")
            est_to_delete = st.selectbox(
                "Seleccionar establecimiento a eliminar:",
                options=[f"{e['nombre']} (ID: {e['id']})" for e in establecimientos_empresa],
                key="delete_est_select"
            )
            
            confirm_delete = st.checkbox(
                "Confirmo eliminar (esto borrará todos los datos asociados)", 
                key="confirm_delete_est"
            )
            
            if st.button("Eliminar Establecimiento", type="secondary", key="btn_delete_est"):
                if confirm_delete:
                    est_id = int(est_to_delete.split("ID: ")[1].replace(")", ""))
                    try:
                        execute_update("DELETE FROM datos_semanales WHERE establecimiento_id = %s", (est_id,))
                        execute_update("DELETE FROM datos_diarios WHERE establecimiento_id = %s", (est_id,))
                        execute_update("DELETE FROM establecimientos WHERE id = %s", (est_id,))
                        st.success("✅ Establecimiento eliminado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("Debes confirmar la eliminación")
        
        # Mover establecimiento
        with col2:
            st.markdown("##### 🔄 Mover a Otra Empresa")
            est_to_move = st.selectbox(
                "Establecimiento a mover:",
                options=[f"{e['nombre']} (ID: {e['id']})" for e in establecimientos_empresa],
                key="move_est_select"
            )
            
            otras_empresas = [e for e in empresas_est if e['id'] != empresa_data_est['id']]
            if otras_empresas:
                target_empresa = st.selectbox(
                    "Mover a empresa:",
                    options=[f"{e['nombre']} ({e['codigo']})" for e in otras_empresas],
                    key="target_empresa_select"
                )
                
                if st.button("Mover Establecimiento", key="btn_move_est"):
                    est_id = int(est_to_move.split("ID: ")[1].replace(")", ""))
                    target_idx = [f"{e['nombre']} ({e['codigo']})" for e in otras_empresas].index(target_empresa)
                    target_empresa_data = otras_empresas[target_idx]
                    try:
                        execute_update(
                            "UPDATE establecimientos SET empresa_id = %s WHERE id = %s",
                            (target_empresa_data['id'], est_id)
                        )
                        execute_update(
                            "UPDATE datos_semanales SET empresa_id = %s WHERE establecimiento_id = %s",
                            (target_empresa_data['id'], est_id)
                        )
                        execute_update(
                            "UPDATE datos_diarios SET empresa_id = %s WHERE establecimiento_id = %s",
                            (target_empresa_data['id'], est_id)
                        )
                        st.success(f"✅ Establecimiento movido a {target_empresa_data['nombre']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            else:
                st.info("No hay otras empresas disponibles")
    else:
        st.warning("Esta empresa no tiene establecimientos registrados")
    
    # Agregar establecimiento manualmente
    st.divider()
    st.subheader("➕ Agregar Establecimiento Manualmente")
    st.caption("Normalmente los establecimientos se crean al subir datos. Usa esto solo para casos especiales.")
    
    with st.form("add_est_form"):
        new_est_nombre = st.text_input("Nombre del establecimiento*")
        new_est_superficie = st.number_input("Superficie praderas (ha)", min_value=0.0, value=0.0)
        
        if st.form_submit_button("Agregar Establecimiento", type="primary"):
            if not new_est_nombre:
                st.error("El nombre es obligatorio")
            else:
                try:
                    execute_query(
                        "INSERT INTO establecimientos (empresa_id, nombre, superficie_praderas) VALUES (%s, %s, %s) RETURNING id",
                        (empresa_data_est['id'], new_est_nombre, new_est_superficie if new_est_superficie > 0 else None),
                        fetch_one=True
                    )
                    st.success(f"✅ Establecimiento '{new_est_nombre}' creado")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
