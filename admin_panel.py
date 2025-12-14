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
from format_utils import format_number_spanish, format_dataframe_for_display
from config_manager import (
    get_filtros_defecto, set_filtros_defecto,
    get_nota_semanal, set_nota_semanal,
    is_nota_visible, set_nota_visible,
    get_orden_defecto, set_orden_defecto
)
import bcrypt
import json

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
# Aplicar estilos visuales (compatible con tema nativo de Streamlit)
from theme_manager import apply_visual_polish
apply_visual_polish()

with st.sidebar:
    st.title("🔐 Admin Panel")
    
    st.write(f"👤 **{st.session_state.nombre_completo}**")
    st.write(f"🏢 Administrador")
    st.divider()
    
    menu = st.radio(
        "Navegación",
        ["📤 Carga de Datos", "👥 Usuarios", "🏢 Empresas", "⚙️ Configuración", "📊 Logs"],
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
        # ========== VISUALIZACIÓN GLOBAL DE MATRIZ ========== #
        st.divider()
        from modules.admin_matrix import show_admin_matrix
        show_admin_matrix()
        # ========== GESTIÓN DE SEMANAS ========== #
        st.divider()
        st.subheader("🗑️ Eliminar semanas cargadas")
        # Obtener períodos disponibles
        periodos = execute_query("""
            SELECT DISTINCT fecha_inicio, fecha_fin
            FROM datos_semanales
            WHERE fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL
            ORDER BY fecha_inicio DESC, fecha_fin DESC
        """)
        periodo_options = [f"{p['fecha_inicio'].strftime('%d-%m-%Y')} al {p['fecha_fin'].strftime('%d-%m-%Y')}" for p in periodos] if periodos else []
        selected_periodo = st.selectbox("Selecciona período a eliminar:", options=periodo_options, key="delete_periodo_select") if periodo_options else None
        if periodo_options:
            confirm_periodo = st.checkbox(f"Confirmo que deseo eliminar el período seleccionado ({selected_periodo})", key="confirm_delete_periodo")
            if st.button("Eliminar período seleccionado", type="secondary", width='stretch', key="btn_delete_periodo"):
                if confirm_periodo:
                    idx = periodo_options.index(selected_periodo)
                    fecha_inicio = periodos[idx]['fecha_inicio']
                    fecha_fin = periodos[idx]['fecha_fin']
                    with st.spinner(f"Eliminando período {fecha_inicio} al {fecha_fin}..."):
                        try:
                            # Obtener establecimiento_ids de este período para eliminar datos_diarios relacionados
                            est_ids = execute_query("SELECT DISTINCT establecimiento_id FROM datos_semanales WHERE fecha_inicio = %s AND fecha_fin = %s", (fecha_inicio, fecha_fin))
                            if est_ids:
                                est_id_list = [e['establecimiento_id'] for e in est_ids]
                                execute_update(f"DELETE FROM datos_diarios WHERE establecimiento_id IN ({','.join(['%s']*len(est_id_list))})", tuple(est_id_list))
                            execute_update("DELETE FROM datos_semanales WHERE fecha_inicio = %s AND fecha_fin = %s", (fecha_inicio, fecha_fin))
                            st.success(f"Período {fecha_inicio} al {fecha_fin} eliminado correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar período: {e}")
                else:
                    st.warning("Debes confirmar la eliminación marcando la casilla.")
        # Botón para eliminar el último período
        if periodos:
            ultimo = periodos[0]
            periodo_str = f"{ultimo['fecha_inicio'].strftime('%d-%m-%Y')} al {ultimo['fecha_fin'].strftime('%d-%m-%Y')}"
            confirm_ultimo = st.checkbox(f"Confirmo que deseo eliminar el último período ({periodo_str})", key="confirm_delete_ultimo")
            if st.button(f"Eliminar último período ({periodo_str})", type="secondary", width='stretch', key="btn_delete_ultimo"):
                if confirm_ultimo:
                    with st.spinner(f"Eliminando último período {periodo_str}..."):
                        try:
                            est_ids = execute_query("SELECT DISTINCT establecimiento_id FROM datos_semanales WHERE fecha_inicio = %s AND fecha_fin = %s", (ultimo['fecha_inicio'], ultimo['fecha_fin']))
                            if est_ids:
                                est_id_list = [e['establecimiento_id'] for e in est_ids]
                                execute_update(f"DELETE FROM datos_diarios WHERE establecimiento_id IN ({','.join(['%s']*len(est_id_list))})", tuple(est_id_list))
                            execute_update("DELETE FROM datos_semanales WHERE fecha_inicio = %s AND fecha_fin = %s", (ultimo['fecha_inicio'], ultimo['fecha_fin']))
                            st.success(f"Último período {periodo_str} eliminado correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar último período: {e}")
                else:
                    st.warning("Debes confirmar la eliminación marcando la casilla.")
        # ========== RESTO DE FLUJO DE CARGA ========== #
        if uploaded_file:
            try:
                import tempfile
                df_semanal = pd.read_excel(uploaded_file)
                st.success(f"✅ Archivo leído: {len(df_semanal)} registros")
                from excel_processor import ExcelProcessor
                processor = ExcelProcessor()
                with st.expander("👁️ Vista previa del archivo subido"):
                    st.dataframe(df_semanal.head(10))
                # Generar preview de la matriz con el DataFrame ya leído
                preview = processor.preview_semanal(df_semanal)
                if preview['success']:
                    from matrix_builder import MATRIX_COLUMNS
                    df_matrix = preview['df_matrix']
                    # Reordenar y mostrar solo las columnas de la matriz general
                    df_matrix = df_matrix.reindex(columns=MATRIX_COLUMNS)
                    with st.expander("🔎 Preview de matriz semanal a ingresar"):
                        df_display, _ = format_dataframe_for_display(df_matrix)
                        st.dataframe(df_display, width='stretch')
                else:
                    st.warning("No se pudo generar preview de la matriz: " + ", ".join(preview.get('errors', [])))

                # Validación básica
                required_cols = ['Empresa', 'Empresa_COD', 'Establecimiento', 'CONCEPTO', 'A. TOTAL']
                missing_cols = [col for col in required_cols if col not in df_semanal.columns]
                if missing_cols:
                    st.error(f"❌ Columnas faltantes: {', '.join(missing_cols)}")
                else:
                    st.success("✅ Estructura válida")
                    if st.button("🚀 Cargar Reporte Semanal", type="primary", width='stretch', key="btn_upload_semanal"):
                        with st.spinner("Procesando reporte semanal..."):
                            result = processor.process_semanal(df_semanal)
                            # Construir resumen y log detallado
                            log_lines = []
                            log_lines.append("=== LOG DE CARGA SEMANAL ===")
                            log_lines.append(f"Archivo: {uploaded_file.name}")
                            log_lines.append(f"Registros procesados: {result['stats'].get('registros_diarios', 0)}")
                            log_lines.append(f"Registros omitidos: {result['stats'].get('registros_omitidos', 0)}")
                            log_lines.append("")
                            
                            # Agregar logs detallados
                            if result.get('logs'):
                                log_lines.append("=== DETALLES DE OMISIONES ===")
                                log_lines.extend(result['logs'])
                                log_lines.append("")
                            
                            # Agregar errores si los hay
                            if result.get('errors'):
                                log_lines.append("=== ERRORES ===")
                                log_lines.extend(result['errors'])
                                log_lines.append("")
                            
                            # Guardar el log en un archivo y hacer descarga automática
                            log_content = '\n'.join(str(line) for line in log_lines)
                            log_filename = f"log_carga_{uploaded_file.name.replace('.xlsx', '').replace('.xls', '')}.txt"
                            
                            # Guardar en carpeta local para acceso rápido
                            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            log_path = os.path.join(log_dir, log_filename)
                            with open(log_path, 'w', encoding='utf-8') as f:
                                f.write(log_content)
                            
                            # Mostrar botón de descarga
                            st.download_button(
                                label="📥 Descargar log de carga",
                                data=log_content,
                                file_name=log_filename,
                                mime="text/plain",
                                key="download_log_semanal"
                            )
                            
                            if result['success']:
                                st.success("✅ Reporte semanal cargado!")
                                col1, col2 = st.columns(2)
                                col1.metric("Registros diarios", result['stats']['registros_diarios'])
                                col2.metric("Registros semanales", result['stats']['registros_semanales'])
                                try:
                                    execute_update(
                                        """
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, registros_procesados, registros_omitidos, estado, mensaje)
                                        VALUES (%s, 'semanal', %s, %s, %s, 'exito', 'Carga semanal exitosa')
                                        """,
                                        (st.session_state.user_id, uploaded_file.name, result['stats']['registros_diarios'], result['stats'].get('registros_omitidos', 0))
                                    )
                                except Exception as log_err:
                                    print(f"Error logging: {log_err}")
                                if result['stats'].get('establecimientos_creados', 0) > 0:
                                    st.info(f"ℹ️ {result['stats']['establecimientos_creados']} establecimientos nuevos creados")
                            else:
                                st.error("❌ Error al cargar reporte semanal")
                                error_msg = "; ".join(result['errors'])
                                for error in result['errors']:
                                    st.error(f"• {error}")
                                try:
                                    execute_update(
                                        """
                                        INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, estado, mensaje)
                                        VALUES (%s, 'semanal', %s, 'error', %s)
                                        """,
                                        (st.session_state.user_id, uploaded_file.name, error_msg)
                                    )
                                except:
                                    pass
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
    
    # -----------------------------
    # TAB 2: HISTÓRICO COMPLETO
    # -----------------------------
    with tab2:
        st.subheader("📊 Histórico Completo de Datos Semanales")
        
        st.info("""
        **Este módulo permite:**
        - Cargar el archivo histórico completo con todos los datos semanales
        - Ver las semanas disponibles en el histórico
        - Consultar datos de cualquier semana pasada
        - Los datos se usan para calcular MDAT 4 sem y 52 sem en la matriz
        """)
        
        # ========== ESTADO DEL HISTÓRICO ========== #
        with st.expander("📈 Estado actual del histórico", expanded=True):
            try:
                # Intentar contar registros del histórico
                hist_count = execute_query("SELECT COUNT(*) as c FROM datos_historicos", fetch_one=True)
                if hist_count:
                    total_registros = hist_count['c']
                    
                    if total_registros > 0:
                        # Obtener resumen
                        resumen = execute_query("""
                            SELECT 
                                COUNT(DISTINCT semana) as semanas,
                                COUNT(DISTINCT establecimiento) as establecimientos,
                                MIN(fecha) as fecha_min,
                                MAX(fecha) as fecha_max
                            FROM datos_historicos
                        """, fetch_one=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Total registros", f"{total_registros:,}")
                        col2.metric("Semanas únicas", resumen['semanas'])
                        col3.metric("Establecimientos", resumen['establecimientos'])
                        col4.metric("Rango fechas", f"{resumen['fecha_min']} - {resumen['fecha_max']}")
                    else:
                        st.warning("⚠️ No hay datos históricos cargados aún")
                else:
                    st.warning("⚠️ Tabla de histórico no encontrada. Ejecuta el script de creación primero.")
            except Exception as e:
                st.warning(f"⚠️ No se pudo obtener estado del histórico: {e}")
                st.info("💡 Si es la primera vez, debes crear la tabla ejecutando `db/create_historico_table.sql`")
        
        # ========== CARGA DE HISTÓRICO ========== #
        st.divider()
        st.subheader("📤 Cargar Archivo Histórico")
        
        st.markdown("""
        **Estructura esperada del Excel histórico:**
        - `semana`: Número de semana del año
        - `Fecha`: Fecha de cierre del período (ej: 03-10-2025)
        - `establecimiento`: Nombre del fundo/establecimiento
        - Columnas de datos: Vacas, Producción, MDAT, etc.
        """)
        
        uploaded_hist = st.file_uploader(
            "Selecciona archivo histórico (Excel)",
            type=['xlsx', 'xls'],
            key="historico_upload"
        )
        
        if uploaded_hist:
            try:
                df_hist = pd.read_excel(uploaded_hist)
                
                st.success(f"✅ Archivo leído: {len(df_hist)} registros, {len(df_hist.columns)} columnas")
                
                with st.expander("👁️ Vista previa del archivo"):
                    st.dataframe(df_hist.head(20))
                
                with st.expander("📋 Columnas detectadas"):
                    st.write(list(df_hist.columns))
                
                # Importar procesador
                from historico_processor import HistoricoProcessor
                processor = HistoricoProcessor()
                
                # Mostrar mapeo de columnas
                col_mapping = processor._map_columns(df_hist)
                with st.expander("🔗 Mapeo de columnas detectado"):
                    if col_mapping:
                        for excel_col, db_col in col_mapping.items():
                            st.write(f"• `{excel_col}` → **{db_col}**")
                    else:
                        st.warning("No se detectaron columnas mapeables")
                
                # Botón de carga
                if st.button("🚀 Cargar Histórico Completo", type="primary", use_container_width=True):
                    with st.spinner("Procesando histórico... esto puede tomar unos minutos"):
                        result = processor.process_historico(df_hist)
                        
                        # Construir log detallado
                        log_lines = []
                        log_lines.append("=== LOG DE CARGA HISTÓRICO ===")
                        log_lines.append(f"Archivo: {uploaded_hist.name}")
                        log_lines.append(f"Filas procesadas: {result['stats'].get('filas_procesadas', 0)}")
                        log_lines.append(f"Filas insertadas: {result['stats'].get('filas_insertadas', 0)}")
                        log_lines.append(f"Filas omitidas: {result['stats'].get('filas_omitidas', 0)}")
                        log_lines.append(f"Semanas únicas: {result['stats'].get('semanas_unicas', 0)}")
                        log_lines.append("")
                        
                        # Agregar logs detallados
                        if result.get('logs'):
                            log_lines.append("=== DETALLES DE OMISIONES ===")
                            log_lines.extend(result['logs'])
                            log_lines.append("")
                        
                        # Agregar errores si los hay
                        if result.get('errors'):
                            log_lines.append("=== ERRORES ===")
                            log_lines.extend(result['errors'])
                            log_lines.append("")
                        
                        # Guardar el log en un archivo
                        log_content = '\n'.join(str(line) for line in log_lines)
                        log_filename = f"log_historico_{uploaded_hist.name.replace('.xlsx', '').replace('.xls', '')}.txt"
                        
                        # Guardar en carpeta local para acceso rápido
                        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
                        os.makedirs(log_dir, exist_ok=True)
                        log_path = os.path.join(log_dir, log_filename)
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write(log_content)
                        
                        # Mostrar botón de descarga
                        st.download_button(
                            label="📥 Descargar log de carga",
                            data=log_content,
                            file_name=log_filename,
                            mime="text/plain",
                            key="download_log_historico"
                        )
                        
                        if result['success']:
                            st.success("✅ Histórico cargado exitosamente!")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Filas procesadas", result['stats']['filas_procesadas'])
                            col2.metric("Filas insertadas", result['stats']['filas_insertadas'])
                            col3.metric("Semanas únicas", result['stats']['semanas_unicas'])
                            
                            if result['stats']['filas_omitidas'] > 0:
                                st.warning(f"⚠️ {result['stats']['filas_omitidas']} filas omitidas (datos incompletos)")
                            
                            # Log
                            try:
                                execute_update("""
                                    INSERT INTO upload_logs (usuario_id, tipo_archivo, nombre_archivo, registros_procesados, registros_omitidos, estado, mensaje)
                                    VALUES (%s, 'historico_completo', %s, %s, %s, 'exito', 'Carga histórica completa exitosa')
                                """, (st.session_state.user_id, uploaded_hist.name, result['stats']['filas_insertadas'], result['stats']['filas_omitidas']))
                            except:
                                pass
                            
                            st.rerun()
                        else:
                            st.error("❌ Error al cargar histórico")
                            for error in result['errors']:
                                st.error(f"• {error}")
                        
            except Exception as e:
                st.error(f"❌ Error al leer archivo: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # ========== VISUALIZACIÓN DE SEMANAS ========== #
        st.divider()
        st.subheader("📅 Semanas Disponibles en el Histórico")
        
        try:
            semanas_disp = execute_query("""
                SELECT 
                    semana,
                    MAX(fecha) as fecha,
                    COUNT(*) as registros,
                    COUNT(DISTINCT establecimiento) as establecimientos
                FROM datos_historicos
                GROUP BY semana
                ORDER BY semana DESC
                LIMIT 100
            """)
            
            if semanas_disp:
                df_semanas = pd.DataFrame(semanas_disp)
                df_semanas['fecha'] = pd.to_datetime(df_semanas['fecha']).dt.strftime('%d-%m-%Y')
                df_semanas.columns = ['Semana', 'Fecha Cierre', 'Registros', 'Establecimientos']
                
                st.dataframe(df_semanas, use_container_width=True, height=400)
                
                # Selector para ver detalle de una semana
                st.divider()
                st.subheader("🔍 Ver Detalle de una Semana")
                
                opciones_semana = [f"Sem {s['Semana']} - {s['Fecha Cierre']}" for _, s in df_semanas.iterrows()]
                selected_sem = st.selectbox("Selecciona una semana:", options=opciones_semana)
                
                if selected_sem and st.button("Ver datos de esta semana"):
                    # Extraer semana del string
                    sem_num = int(selected_sem.split(" ")[1])
                    
                    datos_sem = execute_query("""
                        SELECT 
                            establecimiento,
                            vacas_en_ordena,
                            produccion_total,
                            precio_leche,
                            mdat,
                            porcentaje_grasa,
                            porcentaje_proteina
                        FROM datos_historicos
                        WHERE semana = %s
                        ORDER BY establecimiento
                    """, (sem_num,))
                    
                    if datos_sem:
                        df_detalle = pd.DataFrame(datos_sem)
                        df_detalle.columns = ['Establecimiento', 'Vacas Ordeña', 'Producción', 'Precio Leche', 'MDAT', '% Grasa', '% Proteína']
                        st.dataframe(df_detalle, use_container_width=True)
                    else:
                        st.info("No hay datos para esta semana")
            else:
                st.info("No hay semanas cargadas en el histórico aún")
                
        except Exception as e:
            st.warning(f"No se pudo cargar lista de semanas: {e}")
        
        # ========== ELIMINAR HISTÓRICO ========== #
        st.divider()
        with st.expander("🗑️ Eliminar datos del histórico", expanded=False):
            st.warning("⚠️ Esta acción es irreversible")
            
            confirm_delete_hist = st.checkbox("Confirmo que deseo eliminar TODO el histórico", key="confirm_delete_hist")
            
            if st.button("Eliminar todo el histórico", type="secondary"):
                if confirm_delete_hist:
                    try:
                        execute_update("DELETE FROM datos_historicos")
                        st.success("Histórico eliminado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Debes confirmar la eliminación")

# =====================
# TAB: USUARIOS
# =====================
elif menu == "👥 Usuarios":
    st.header("👥 Gestión de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["Lista de Usuarios", "Crear Usuario", "🔑 Cambiar Contraseña"])
    
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
    
    # -------------------------
    # TAB 3: CAMBIAR CONTRASEÑA
    # -------------------------
    with tab3:
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

# =====================
# TAB: EMPRESAS
# =====================
elif menu == "🏢 Empresas":
    st.header("🏢 Gestión de Empresas")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Lista de Empresas", "Crear Empresa", "Editar Empresa", "📍 Establecimientos"])
    
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
        
        empresas_edit = execute_query("SELECT id, codigo, nombre, color_primario, logo_url FROM empresas ORDER BY nombre")
        
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
                            # Guardar None si el color es el por defecto o logo está vacío
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
    
    # -------------------------
    # TAB 4: ESTABLECIMIENTOS
    # -------------------------
    with tab4:
        st.subheader("📍 Gestión de Establecimientos")
        
        st.info("""
        **¿Cómo se crean los establecimientos?**
        - Los establecimientos se crean **automáticamente** cuando subes un reporte semanal
        - El sistema asocia cada establecimiento del Excel a la empresa indicada en el archivo
        - Aquí puedes ver, editar y reorganizar los establecimientos existentes
        """)
        
        # Selector de empresa
        empresas_est = execute_query("SELECT id, codigo, nombre FROM empresas ORDER BY nombre")
        
        if empresas_est:
            empresa_select_dict = {f"{e['nombre']} ({e['codigo']})": e for e in empresas_est}
            selected_empresa_est = st.selectbox(
                "Seleccionar empresa:",
                options=list(empresa_select_dict.keys()),
                key="est_empresa_select"
            )
            
            empresa_data_est = empresa_select_dict[selected_empresa_est]
            
            # Obtener establecimientos de esta empresa
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
                
                # Acciones
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
                    
                    confirm_delete = st.checkbox("Confirmo eliminar (esto borrará todos los datos asociados)", key="confirm_delete_est")
                    
                    if st.button("Eliminar Establecimiento", type="secondary", key="btn_delete_est"):
                        if confirm_delete:
                            # Extraer ID
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
                
                # Mover establecimiento a otra empresa
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
                            target_empresa_data = otras_empresas[[f"{e['nombre']} ({e['codigo']})" for e in otras_empresas].index(target_empresa)]
                            try:
                                execute_update(
                                    "UPDATE establecimientos SET empresa_id = %s WHERE id = %s",
                                    (target_empresa_data['id'], est_id)
                                )
                                # También actualizar datos_semanales y datos_diarios
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
        else:
            st.warning("No hay empresas registradas. Crea una empresa primero.")

# =====================
# TAB: CONFIGURACIÓN
# =====================
elif menu == "⚙️ Configuración":
    st.header("⚙️ Configuración de la Aplicación")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Filtros por Defecto", "📝 Notas Semanales", "🔀 Ordenamiento", "🎨 Temas"])
    
    # -------------------------
    # TAB 1: FILTROS POR DEFECTO
    # -------------------------
    with tab1:
        st.subheader("🎯 Establecimientos Preseleccionados")
        st.info("""
        Define qué establecimientos aparecerán **preseleccionados** cuando los usuarios abran la aplicación.
        Los usuarios podrán cambiar esta selección, pero estos serán los valores iniciales.
        """)
        
        # Obtener todos los establecimientos disponibles
        establecimientos = execute_query("""
            SELECT DISTINCT nombre FROM establecimientos ORDER BY nombre
        """)
        
        if establecimientos:
            est_options = [e['nombre'] for e in establecimientos]
            
            # Cargar configuración actual
            filtros_actuales = get_filtros_defecto()
            
            # Filtrar solo los que existen actualmente
            filtros_validos = [f for f in filtros_actuales if f in est_options]
            
            selected_filtros = st.multiselect(
                "Selecciona establecimientos por defecto:",
                options=est_options,
                default=filtros_validos,
                help="Estos establecimientos estarán preseleccionados al cargar la app"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar Filtros", type="primary", use_container_width=True):
                    if set_filtros_defecto(selected_filtros, st.session_state.user_id):
                        st.success(f"✅ Guardado! {len(selected_filtros)} establecimientos por defecto")
                    else:
                        st.error("❌ Error al guardar")
            
            with col2:
                if st.button("🔄 Seleccionar Todos", use_container_width=True):
                    if set_filtros_defecto(est_options, st.session_state.user_id):
                        st.success("✅ Todos los establecimientos seleccionados por defecto")
                        st.rerun()
            
            st.divider()
            st.caption(f"**Configuración actual:** {len(filtros_validos)} establecimientos seleccionados")
        else:
            st.warning("No hay establecimientos registrados aún")
    
    # -------------------------
    # TAB 2: NOTAS SEMANALES
    # -------------------------
    with tab2:
        st.subheader("📝 Nota Semanal para Usuarios")
        st.info("""
        Escribe una nota que aparecerá en la parte superior de la **Matriz Semanal** para todos los usuarios.
        Útil para comunicar novedades, alertas o información importante de la semana.
        """)
        
        # Cargar nota actual
        nota_actual = get_nota_semanal() or ""
        nota_visible = is_nota_visible()
        
        # Editor de nota
        nueva_nota = st.text_area(
            "Contenido de la nota:",
            value=nota_actual,
            height=150,
            placeholder="Escribe aquí la nota para esta semana...\n\nEjemplo:\n📢 Esta semana se actualizaron los precios de leche.\n⚠️ Revisar datos de producción de Fundo X.",
            help="Puedes usar emojis para hacer la nota más visual"
        )
        
        mostrar_nota = st.checkbox("📣 Mostrar nota a los usuarios", value=nota_visible)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar Nota", type="primary", use_container_width=True):
                success = True
                if not set_nota_semanal(nueva_nota, st.session_state.user_id):
                    success = False
                if not set_nota_visible(mostrar_nota, st.session_state.user_id):
                    success = False
                
                if success:
                    st.success("✅ Nota guardada!")
                else:
                    st.error("❌ Error al guardar nota")
        
        with col2:
            if st.button("🗑️ Borrar Nota", use_container_width=True):
                if set_nota_semanal("", st.session_state.user_id):
                    st.success("✅ Nota eliminada")
                    st.rerun()
        
        # Preview
        if nueva_nota and mostrar_nota:
            st.divider()
            st.caption("**Vista previa de la nota:**")
            st.info(nueva_nota)
    
    # -------------------------
    # TAB 3: ORDENAMIENTO POR DEFECTO
    # -------------------------
    with tab3:
        st.subheader("🔀 Ordenamiento por Defecto de la Matriz")
        st.info("""
        Define el **orden inicial** de la Matriz Semanal cuando los usuarios abran la aplicación.
        Los usuarios podrán cambiar el orden, pero este será el valor por defecto.
        """)
        
        # Lista de columnas típicas de la matriz
        columnas_matriz = [
            "Establecimiento",
            "Superficie Praderas",
            "Vacas masa",
            "Vacas en ordeña", 
            "Carga animal",
            "Porcentaje de grasa",
            "Proteinas",
            "Costo promedio concentrado",
            "Grms concentrado / ltr leche",
            "Concentrado",
            "Forrajes conservados",
            "Praderas y otros verdes",
            "Total MS",
            "Producción promedio",
            "Precio de la leche",
            "Costo ración vaca",
            "MDAT",
            "Ranking MDAT",
            "MDAT 4 sem",
            "MDAT 52 sem"
        ]
        
        # Cargar configuración actual
        orden_actual = get_orden_defecto()
        
        col1, col2 = st.columns(2)
        
        with col1:
            columna_index = columnas_matriz.index(orden_actual['columna']) if orden_actual['columna'] in columnas_matriz else 0
            columna_seleccionada = st.selectbox(
                "Ordenar por columna:",
                options=columnas_matriz,
                index=columna_index,
                key="config_orden_columna"
            )
        
        with col2:
            direccion = st.radio(
                "Dirección:",
                options=["↑ Ascendente", "↓ Descendente"],
                index=0 if orden_actual['ascendente'] else 1,
                horizontal=True,
                key="config_orden_dir"
            )
        
        es_ascendente = direccion == "↑ Ascendente"
        
        if st.button("💾 Guardar Ordenamiento", type="primary", use_container_width=True):#
            if set_orden_defecto(columna_seleccionada, es_ascendente, st.session_state.user_id):
                st.success(f"✅ Guardado: Ordenar por **{columna_seleccionada}** ({'Ascendente' if es_ascendente else 'Descendente'})")
            else:
                st.error("❌ Error al guardar")
        
        st.divider()
        st.caption(f"**Configuración actual:** Ordenar por **{orden_actual['columna']}** ({'Ascendente' if orden_actual['ascendente'] else 'Descendente'})")
    
    # -------------------------
    # TAB 4: TEMAS
    # -------------------------
    with tab4:
        st.subheader("🎨 Configuración de Temas")
        st.info("""
        Configura la apariencia visual de la aplicación:
        - **Tema por defecto:** El tema (claro/oscuro) que ven nuevos usuarios al acceder
        - **Colores por empresa:** Configura en la pestaña 'Empresas' → 'Editar Empresa'
        - **Logos por empresa:** Configura en la pestaña 'Empresas' → 'Editar Empresa'
        """)
        
        from theme_manager import get_default_theme, set_default_theme, THEMES
        
        # Tema por defecto global
        current_default = get_default_theme()
        
        st.markdown("##### 🌓 Tema por Defecto Global")
        
        col1, col2 = st.columns(2)
        
        with col1:
            theme_option = st.radio(
                "Selecciona el tema por defecto:",
                options=['light', 'dark'],
                format_func=lambda x: f"{THEMES[x]['icon']} {THEMES[x]['name']}",
                index=0 if current_default == 'light' else 1,
                key="config_tema_defecto",
                horizontal=True
            )
        
        with col2:
            if st.button("💾 Guardar Tema por Defecto", type="primary", use_container_width=True):
                if set_default_theme(theme_option, st.session_state.user_id):
                    st.success(f"✅ Tema por defecto: {THEMES[theme_option]['icon']} {THEMES[theme_option]['name']}")
                else:
                    st.error("❌ Error al guardar")
        
        st.divider()
        
        # Preview de temas
        st.markdown("##### 👁️ Vista Previa de Temas")
        
        preview_col1, preview_col2 = st.columns(2)
        
        with preview_col1:
            st.markdown(f"""
            <div style="
                background: #FFFFFF;
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 1rem;
                text-align: center;
            ">
                <h4 style="color: #1E1E1E; margin: 0;">☀️ Tema Claro</h4>
                <p style="color: #4A4A4A; font-size: 0.9rem;">Fondo blanco, texto oscuro</p>
                <div style="
                    background: #00C853;
                    color: white;
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    display: inline-block;
                    margin-top: 0.5rem;
                ">Botón Acento</div>
            </div>
            """, unsafe_allow_html=True)
        
        with preview_col2:
            st.markdown(f"""
            <div style="
                background: #0E1117;
                border: 2px solid #30363D;
                border-radius: 12px;
                padding: 1rem;
                text-align: center;
            ">
                <h4 style="color: #F0F6FC; margin: 0;">🌙 Tema Oscuro</h4>
                <p style="color: #C9D1D9; font-size: 0.9rem;">Fondo oscuro, texto claro</p>
                <div style="
                    background: #00C853;
                    color: white;
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    display: inline-block;
                    margin-top: 0.5rem;
                ">Botón Acento</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        st.caption(f"**Configuración actual:** Tema por defecto {THEMES[current_default]['icon']} {THEMES[current_default]['name']}")


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
