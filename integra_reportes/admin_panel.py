"""
Panel de Administración - Integra SpA
Sistema de carga de datos y gestión de usuarios/RLS
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
import sys
import os

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from auth import require_auth, init_session_state, logout
from db_connection import execute_query, execute_update
import bcrypt

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="Admin Panel - Integra SpA",
    page_icon="🔐",
    layout="wide"
)

# =====================
# AUTH
# =====================
init_session_state()

if not require_auth():
    st.stop()

# Verificar que sea admin
if not st.session_state.get('is_admin', False):
    st.error("⛔ Acceso denegado. Solo administradores pueden acceder a este panel.")
    st.info("Contacta al administrador del sistema para obtener permisos.")
    st.stop()

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.title("🔐 Admin Panel")
    st.write(f"👤 **{st.session_state.nombre_completo}**")
    st.write(f"🏢 Administrador")
    st.divider()
    
    menu = st.radio(
        "Navegación",
        ["📤 Carga de Datos", "👥 Usuarios", "🏢 Empresas", "📊 Logs"],
        label_visibility="collapsed"
    )
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        logout()
        st.rerun()

# =====================
# MAIN CONTENT
# =====================
st.title("Panel de Administración")

# =====================
# TAB: CARGA DE DATOS
# =====================
if menu == "📤 Carga de Datos":
    st.header("📤 Carga de Datos desde Excel")

    # ================= ESTADO ACTUAL BD =================
    with st.expander("🧾 Estado actual de la base de datos", expanded=False):
        try:
            semana_row = execute_query("SELECT MAX(semana) AS semana, MAX(anio) AS anio FROM datos_semanales", fetch_one=True)
            diarios_count = execute_query("SELECT COUNT(*) AS c FROM datos_diarios", fetch_one=True)['c']
            semanales_count = execute_query("SELECT COUNT(*) AS c FROM datos_semanales", fetch_one=True)['c']
            historico_count = execute_query("SELECT COUNT(*) AS c FROM historico_mdat", fetch_one=True)['c']
            st.write(f"Semana cargada más reciente: **{semana_row['semana']} / {semana_row['anio']}**")
            colA, colB, colC = st.columns(3)
            colA.metric("Registros diarios", f"{diarios_count}")
            colB.metric("Registros semanales", f"{semanales_count}")
            colC.metric("Histórico MDAT", f"{historico_count}")
        except Exception as _e:
            st.warning("No se pudo obtener estado actual: " + str(_e))
    
    tab1, tab2 = st.tabs(["Reporte Semanal", "Histórico MDAT"])
    
    # -----------------------------
    # TAB 1: REPORTE SEMANAL
    # -----------------------------
    with tab1:
        st.subheader("Upload Reporte Semanal")
        
        st.info("""
        **Estructura esperada del Excel:**
        - Columnas: `Empresa`, `Empresa_COD`, `Establecimiento`, `CATEGORIA`, `CONCEPTO`, `<fechas>`, `A. TOTAL`
        - Fechas en formato: `27-09-2025`, `28-09-2025`, etc.
        - Este archivo se sube SEMANALMENTE
        """)
        
        uploaded_file = st.file_uploader(
            "Selecciona archivo Excel",
            type=['xlsx', 'xls'],
            key="semanal_upload"
        )
        
        if uploaded_file:
            try:
                # Leer Excel
                df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ Archivo leído: {len(df)} registros")
                
                # Mostrar preview
                with st.expander("👁️ Vista previa (primeras 10 filas)"):
                    st.dataframe(df.head(10))
                
                # Validación de estructura
                st.subheader("🔍 Validación de Estructura")
                
                required_cols = ['Empresa_COD', 'Establecimiento', 'CATEGORIA', 'CONCEPTO']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ Columnas faltantes: {', '.join(missing_cols)}")
                else:
                    st.success("✅ Estructura válida")
                
                # Detectar columnas de fecha
                import re
                date_pattern = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}$')
                date_cols = [col for col in df.columns if date_pattern.match(str(col))]
                
                st.metric("Columnas de fecha detectadas", len(date_cols))
                
                if date_cols:
                    fecha_rango = f"{date_cols[0]} a {date_cols[-1]}"
                    st.info(f"📅 Rango: {fecha_rango}")
                
                # Análisis de empresas
                st.subheader("🏢 Empresas detectadas")
                
                if 'Empresa_COD' in df.columns:
                    empresas_en_excel = df['Empresa_COD'].dropna().unique()
                    
                    # Obtener empresas en BD
                    empresas_bd = execute_query("SELECT codigo, nombre FROM empresas")
                    empresas_bd_dict = {e['codigo']: e['nombre'] for e in empresas_bd}
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**En Excel (Homologado):**")
                        for emp_cod_raw in empresas_en_excel:
                            # Simular homologación
                            emp_cod_clean = str(emp_cod_raw).split('_')[0].strip()
                            
                            if emp_cod_clean in empresas_bd_dict:
                                if emp_cod_clean != str(emp_cod_raw):
                                    st.write(f"✅ {emp_cod_raw} ➡️ {emp_cod_clean} ({empresas_bd_dict[emp_cod_clean]})")
                                else:
                                    st.write(f"✅ {emp_cod_clean} - {empresas_bd_dict[emp_cod_clean]}")
                            else:
                                st.write(f"⚠️ {emp_cod_raw} (Clean: {emp_cod_clean}) - **NO EXISTE EN BD**")
                    
                    with col2:
                        st.write("**En Base de Datos:**")
                        for cod, nombre in empresas_bd_dict.items():
                            st.write(f"• {cod} - {nombre}")
                
                # Botón de procesamiento
                st.divider()
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    semana_manual = st.number_input("Semana (opcional)", min_value=1, max_value=53, value=None)
                with col2:
                    anio_manual = st.number_input("Año (opcional)", min_value=2020, max_value=2030, value=None)
                
                if st.button("🚀 Procesar y Cargar Datos", type="primary", use_container_width=True):
                    if missing_cols:
                        st.error("No se puede procesar: faltan columnas requeridas")
                    else:
                        with st.spinner("Procesando datos..."):
                            from excel_processor import ExcelProcessor
                            
                            processor = ExcelProcessor()
                            result = processor.process_semanal(df, semana=semana_manual, anio=anio_manual)
                            
                            if result['success']:
                                st.success("✅ Datos procesados exitosamente!")
                                
                                stats = result['stats']
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Empresas", stats['empresas_procesadas'])
                                with col2:
                                    st.metric("Establecimientos", stats['establecimientos_creados'])
                                with col3:
                                    st.metric("Datos Diarios", stats['registros_diarios'])
                                with col4:
                                    st.metric("Datos Semanales", stats['registros_semanales'])
                                
                                # Log success
                                try:
                                    execute_update("""
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, registros_procesados, estado, mensaje)
                                        VALUES (%s, 'semanal', %s, %s, 'exito', %s)
                                    """, (st.session_state.user_id, uploaded_file.name, stats['registros_diarios'], "Carga exitosa"))
                                except Exception as log_err:
                                    print(f"Error logging: {log_err}")

                                if result.get('warnings'):
                                    st.warning("⚠️ Advertencias:")
                                    for warning in result['warnings']:
                                        st.write(f"- {warning}")
                            else:
                                st.error("❌ Error en el procesamiento")
                                error_msg = "; ".join(result['errors'])
                                for error in result['errors']:
                                    st.error(f"• {error}")
                # ===== Preview Matriz (sin persistir) =====
                st.divider()
                st.subheader("🔍 Previsualizar Matriz (sin guardar)")
                if st.button("Generar Preview", use_container_width=True):
                    from excel_processor import ExcelProcessor
                    processor_preview = ExcelProcessor()
                    preview = processor_preview.preview_semanal(df)
                    if not preview.get('success'):
                        st.error("No se pudo generar preview: " + "; ".join(preview.get('errors', [])))
                    else:
                        st.info(f"Semana detectada: {preview['semana']} / {preview['anio']}")
                        df_matrix_prev = preview['df_matrix']
                        st.dataframe(df_matrix_prev, use_container_width=True, height=400)
                        st.caption("Esta matriz proviene únicamente del Excel subido y no refleja datos ya guardados en la BD.")

                # ===== Eliminar semana cargada =====
                st.divider()
                st.subheader("🧹 Eliminar Semana de la BD")
                semana_del = st.number_input("Semana a eliminar", min_value=1, max_value=53, value=0, step=1)
                anio_del = st.number_input("Año a eliminar", min_value=2020, max_value=2035, value=0, step=1)
                col_del1, col_del2 = st.columns([1,2])
                with col_del1:
                    confirm_delete = st.checkbox("Confirmo eliminación irreversible")
                with col_del2:
                    if st.button("🗑️ Eliminar Semana", type="secondary", use_container_width=True, disabled=not confirm_delete or semana_del==0 or anio_del==0):
                        if semana_del == 0 or anio_del == 0:
                            st.error("Debe ingresar semana y año válidos")
                        else:
                            try:
                                sem_rows = execute_query("SELECT COUNT(*) AS c FROM datos_semanales WHERE semana=%s AND anio=%s", (semana_del, anio_del), fetch_one=True)['c']
                                dia_rows = execute_query("SELECT COUNT(*) AS c FROM datos_diarios WHERE EXTRACT(WEEK FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (semana_del, anio_del), fetch_one=True)['c']
                                hist_rows = execute_query("SELECT COUNT(*) AS c FROM historico_mdat WHERE semana=%s AND anio=%s", (semana_del, anio_del), fetch_one=True)['c']
                                execute_update("DELETE FROM datos_semanales WHERE semana=%s AND anio=%s", (semana_del, anio_del))
                                execute_update("DELETE FROM datos_diarios WHERE EXTRACT(WEEK FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (semana_del, anio_del))
                                execute_update("DELETE FROM historico_mdat WHERE semana=%s AND anio=%s", (semana_del, anio_del))
                                st.success(f"Semana {semana_del}/{anio_del} eliminada. Semanales: {sem_rows}, Diarios: {dia_rows}, Histórico: {hist_rows}.")
                            except Exception as del_err:
                                st.error("Error al eliminar semana: " + str(del_err))
                                st.exception(del_err)
                                
                                # Log error
                                try:
                                    execute_update("""
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, estado, mensaje)
                                        VALUES (%s, 'semanal', %s, 'error', %s)
                                    """, (st.session_state.user_id, uploaded_file.name, error_msg))
                                except:
                                    pass
                
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {e}")
                st.exception(e)
    
    # -----------------------------
    # TAB 2: HISTÓRICO MDAT
    # -----------------------------
    with tab2:
        st.subheader("Upload Histórico MDAT")
        
        st.info("""
        **Estructura esperada:**
        - Columnas: `Empresa`, `N° Semana`, `Año`, `(I) MDAT`, `Vacas en ordeña`
        - Este archivo se carga **UNA SOLA VEZ** al inicio
        """)
        
        uploaded_hist = st.file_uploader(
            "Selecciona archivo histórico",
            type=['xlsx', 'xls'],
            key="historico_upload"
        )
        
        if uploaded_hist:
            try:
                df_hist = pd.read_excel(uploaded_hist)
                
                st.success(f"✅ Archivo leído: {len(df_hist)} registros")
                
                with st.expander("👁️ Vista previa"):
                    st.dataframe(df_hist.head(10))
                
                # Validación
                required_hist = ['Empresa', 'N° Semana', '(I) MDAT']
                missing_hist = [col for col in required_hist if col not in df_hist.columns]
                
                if missing_hist:
                    st.error(f"❌ Columnas faltantes: {', '.join(missing_hist)}")
                else:
                    st.success("✅ Estructura válida")
                    
                    if st.button("🚀 Cargar Histórico", type="primary", use_container_width=True):
                        with st.spinner("Procesando histórico..."):
                            from excel_processor import ExcelProcessor
                            
                            processor = ExcelProcessor()
                            result = processor.process_historico(df_hist)
                            
                            if result['success']:
                                st.success("✅ Histórico cargado!")
                                st.metric("Registros insertados", result['stats']['inserted'])
                                
                                # Log success
                                try:
                                    execute_update("""
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, registros_procesados, registros_omitidos, estado, mensaje)
                                        VALUES (%s, 'historico', %s, %s, %s, 'exito', 'Carga histórica exitosa')
                                    """, (st.session_state.user_id, uploaded_hist.name, result['stats']['inserted'], result['stats']['skipped']))
                                except Exception as log_err:
                                    print(f"Error logging: {log_err}")

                                if result['stats']['skipped'] > 0:
                                    st.warning(f"⚠️ {result['stats']['skipped']} registros omitidos (establecimiento no encontrado)")
                            else:
                                st.error("❌ Error al cargar histórico")
                                error_msg = "; ".join(result['errors'])
                                for error in result['errors']:
                                    st.error(f"• {error}")
                                
                                # Log error
                                try:
                                    execute_update("""
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, estado, mensaje)
                                        VALUES (%s, 'historico', %s, 'error', %s)
                                    """, (st.session_state.user_id, uploaded_hist.name, error_msg))
                                except:
                                    pass
                        
            except Exception as e:
                st.error(f"❌ Error: {e}")

# =====================
# TAB: USUARIOS
# =====================
elif menu == "👥 Usuarios":
    st.header("👥 Gestión de Usuarios")
    
    tab1, tab2 = st.tabs(["Lista de Usuarios", "Crear Usuario"])
    
    with tab1:
        # Listar usuarios
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
    
    with tab2:
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
                empresas_options = {e['id']: e['nombre'] for e in empresas}
                
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

# =====================
# TAB: EMPRESAS
# =====================
elif menu == "🏢 Empresas":
    st.header("🏢 Gestión de Empresas")
    
    tab1, tab2, tab3 = st.tabs(["Lista de Empresas", "Crear Empresa", "Editar Empresa"])
    
    # -------------------------
    # TAB 1: LISTA
    # -------------------------
    with tab1:
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
            
            # Agregar botones de acción
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
                    
                    # Verificar si tiene datos
                    check = execute_query(
                        "SELECT COUNT(*) as count FROM datos_semanales WHERE empresa_id = %s",
                        (empresa_id,),
                        fetch_one=True
                    )
                    
                    if check['count'] > 0:
                        st.error(f"❌ No se puede eliminar: tiene {check['count']} registros de datos")
                    else:
                        try:
                            execute_update("DELETE FROM empresas WHERE id = %s", (empresa_id,))
                            st.success("✅ Empresa eliminada")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        else:
            st.info("No hay empresas registradas")
    
    # -------------------------
    # TAB 2: CREAR
    # -------------------------
    with tab2:
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
    
    # -------------------------
    # TAB 3: EDITAR
    # -------------------------
    with tab3:
        st.subheader("Editar Empresa")
        
        empresas_edit = execute_query("SELECT id, codigo, nombre FROM empresas ORDER BY nombre")
        
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
                
                submitted_edit = st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True)
                
                if submitted_edit:
                    if not new_codigo or not new_nombre:
                        st.error("❌ Todos los campos son obligatorios")
                    else:
                        try:
                            execute_update(
                                "UPDATE empresas SET codigo = %s, nombre = %s WHERE id = %s",
                                (new_codigo, new_nombre, empresa_data['id'])
                            )
                            st.success("✅ Empresa actualizada!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        else:
            st.info("No hay empresas para editar")


# =====================
# TAB: LOGS
# =====================
elif menu == "📊 Logs":
    st.header("📊 Logs del Sistema")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        tipo_filter = st.multiselect("Tipo de Archivo", ["semanal", "historico"], default=["semanal", "historico"])
    with col2:
        estado_filter = st.multiselect("Estado", ["exito", "error", "warning"], default=["exito", "error", "warning"])
    
    # Query logs
    query = """
        SELECT l.id, l.fecha_carga, u.username, l.tipo_archivo, l.nombre_archivo, 
               l.registros_procesados, l.estado, l.mensaje
        FROM upload_logs l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        ORDER BY l.fecha_carga DESC
        LIMIT 100
    """
    
    try:
        logs = execute_query(query)
    except Exception as e:
        if 'upload_logs' in str(e):
            st.warning("Tabla 'upload_logs' no existe. Creándola...")
            try:
                execute_update("""
                    CREATE TABLE upload_logs (
                        id SERIAL PRIMARY KEY,
                        usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                        fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tipo_archivo VARCHAR(50),
                        nombre_archivo VARCHAR(255),
                        registros_procesados INTEGER,
                        registros_omitidos INTEGER,
                        estado VARCHAR(50),
                        mensaje TEXT
                    );
                """)
                st.success("Tabla 'upload_logs' creada. No hay registros aún.")
                logs = []
            except Exception as ddl_err:
                st.error("No se pudo crear tabla 'upload_logs': " + str(ddl_err))
                logs = []
        else:
            st.error("Error obteniendo logs: " + str(e))
            logs = []
    
    if logs and len(logs) > 0:
        df_logs = pd.DataFrame(logs)
        
        # Formatear fecha
        df_logs['fecha_carga'] = pd.to_datetime(df_logs['fecha_carga']).dt.strftime('%d-%m-%Y %H:%M')
        
        # Filtrar en pandas (más fácil que SQL dinámico aquí)
        if tipo_filter:
            df_logs = df_logs[df_logs['tipo_archivo'].isin(tipo_filter)]
        if estado_filter:
            df_logs = df_logs[df_logs['estado'].isin(estado_filter)]
            
        # Mapear iconos
        df_logs['Estado'] = df_logs['estado'].map({
            'exito': '✅',
            'error': '❌',
            'warning': '⚠️'
        })
        
        st.dataframe(
            df_logs[['fecha_carga', 'username', 'tipo_archivo', 'nombre_archivo', 'registros_procesados', 'Estado', 'mensaje']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay registros de actividad")
