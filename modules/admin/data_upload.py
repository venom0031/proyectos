# =====================================================
# MÓDULO: Carga de Datos
# =====================================================
"""
Funciones para renderizar la carga de datos en el admin panel.
Este módulo mantiene la lógica existente pero la encapsula en funciones.
"""

import streamlit as st
import pandas as pd
import os

from db_connection import execute_query, execute_update


def render_data_upload_tab():
    """
    Renderiza la pestaña completa de carga de datos.
    
    NOTA: Este módulo es un wrapper que encapsula la lógica existente.
    La implementación completa permanece en admin_panel.py por ahora
    debido a su complejidad y dependencias.
    """
    st.header("📤 Carga de Datos desde Excel")
    
    # Estado actual de la BD
    _render_db_status()
    
    # Tabs de carga
    tab1, tab2 = st.tabs(["Reporte Semanal", "Histórico MDAT"])
    
    with tab1:
        _render_semanal_upload()
    
    with tab2:
        _render_historico_upload()


def _render_db_status():
    """Muestra el estado actual de la base de datos."""
    with st.expander("🧾 Estado actual de la base de datos", expanded=False):
        try:
            semana_row = execute_query(
                "SELECT MAX(semana) AS semana, MAX(anio) AS anio FROM datos_semanales", 
                fetch_one=True
            )
            diarios_count = execute_query("SELECT COUNT(*) AS c FROM datos_diarios", fetch_one=True)['c']
            semanales_count = execute_query("SELECT COUNT(*) AS c FROM datos_semanales", fetch_one=True)['c']
            historico_count = execute_query("SELECT COUNT(*) AS c FROM historico_mdat", fetch_one=True)['c']
            
            if semana_row and semana_row['semana']:
                st.write(f"Semana cargada más reciente: **{semana_row['semana']} / {semana_row['anio']}**")
            else:
                st.write("No hay datos semanales cargados")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Registros diarios", f"{diarios_count:,}")
            col2.metric("Registros semanales", f"{semanales_count:,}")
            col3.metric("Histórico MDAT", f"{historico_count:,}")
        except Exception as e:
            st.warning(f"No se pudo obtener estado actual: {e}")


def _render_semanal_upload():
    """Renderiza la sección de carga de reporte semanal."""
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
        key="semanal_upload_module"
    )
    
    if uploaded_file:
        try:
            df_semanal = pd.read_excel(uploaded_file)
            st.success(f"✅ Archivo leído: {len(df_semanal)} registros")
            
            # Vista previa
            with st.expander("👁️ Vista previa del archivo subido"):
                st.dataframe(df_semanal.head(10))
            
            # Validación básica
            required_cols = ['Empresa', 'Empresa_COD', 'Establecimiento', 'CONCEPTO', 'A. TOTAL']
            missing_cols = [col for col in required_cols if col not in df_semanal.columns]
            
            if missing_cols:
                st.error(f"❌ Columnas faltantes: {', '.join(missing_cols)}")
            else:
                st.success("✅ Estructura válida")
                
                if st.button("🚀 Cargar Reporte Semanal", type="primary", use_container_width=True):
                    _process_semanal_upload(uploaded_file, df_semanal)
                    
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")


def _process_semanal_upload(uploaded_file, df_semanal):
    """Procesa la carga del reporte semanal."""
    from excel_processor import ExcelProcessor
    
    with st.spinner("Procesando reporte semanal..."):
        processor = ExcelProcessor()
        result = processor.process_semanal(df_semanal)
        
        # Construir log
        log_lines = [
            "=== LOG DE CARGA SEMANAL ===",
            f"Archivo: {uploaded_file.name}",
            f"Registros procesados: {result['stats'].get('registros_diarios', 0)}",
            f"Registros omitidos: {result['stats'].get('registros_omitidos', 0)}",
            ""
        ]
        
        if result.get('logs'):
            log_lines.append("=== DETALLES DE OMISIONES ===")
            log_lines.extend(result['logs'])
            log_lines.append("")
        
        if result.get('errors'):
            log_lines.append("=== ERRORES ===")
            log_lines.extend(result['errors'])
            log_lines.append("")
        
        # Guardar y mostrar log
        log_content = '\n'.join(str(line) for line in log_lines)
        log_filename = f"log_carga_{uploaded_file.name.replace('.xlsx', '').replace('.xls', '')}.txt"
        
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, log_filename)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        st.download_button(
            label="📥 Descargar log de carga",
            data=log_content,
            file_name=log_filename,
            mime="text/plain",
            key="download_log_semanal_module"
        )
        
        if result['success']:
            st.success("✅ Reporte semanal cargado!")
            col1, col2 = st.columns(2)
            col1.metric("Registros diarios", result['stats']['registros_diarios'])
            col2.metric("Registros semanales", result['stats']['registros_semanales'])
            
            if result['stats'].get('establecimientos_creados', 0) > 0:
                st.info(f"ℹ️ {result['stats']['establecimientos_creados']} establecimientos nuevos creados")
        else:
            st.error("❌ Error al cargar reporte semanal")
            for error in result['errors']:
                st.error(f"• {error}")


def _render_historico_upload():
    """Renderiza la sección de carga de histórico."""
    st.subheader("📊 Histórico Completo de Datos Semanales")
    
    st.info("""
    **Este módulo permite:**
    - Cargar el archivo histórico completo con todos los datos semanales
    - Ver las semanas disponibles en el histórico
    - Consultar datos de cualquier semana pasada
    - Los datos se usan para calcular MDAT 4 sem y 52 sem en la matriz
    """)
    
    # Estado del histórico
    _render_historico_status()
    
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
        key="historico_upload_module"
    )
    
    if uploaded_hist:
        try:
            df_hist = pd.read_excel(uploaded_hist)
            st.success(f"✅ Archivo leído: {len(df_hist)} registros, {len(df_hist.columns)} columnas")
            
            with st.expander("👁️ Vista previa del archivo"):
                st.dataframe(df_hist.head(20))
            
            with st.expander("📋 Columnas detectadas"):
                st.write(list(df_hist.columns))
            
            if st.button("🚀 Cargar Histórico Completo", type="primary", use_container_width=True):
                _process_historico_upload(uploaded_hist, df_hist)
                
        except Exception as e:
            st.error(f"❌ Error al leer archivo: {e}")
            import traceback
            st.code(traceback.format_exc())


def _render_historico_status():
    """Muestra el estado actual del histórico."""
    with st.expander("📈 Estado actual del histórico", expanded=True):
        try:
            hist_count = execute_query("SELECT COUNT(*) as c FROM datos_historicos", fetch_one=True)
            if hist_count and hist_count['c'] > 0:
                total_registros = hist_count['c']
                
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
        except Exception as e:
            st.warning(f"⚠️ No se pudo obtener estado del histórico: {e}")
            st.info("💡 Si es la primera vez, debes crear la tabla ejecutando `db/create_historico_table.sql`")


def _process_historico_upload(uploaded_hist, df_hist):
    """Procesa la carga del histórico."""
    from historico_processor import HistoricoProcessor
    
    with st.spinner("Procesando histórico... esto puede tomar unos minutos"):
        processor = HistoricoProcessor()
        result = processor.process_historico(df_hist)
        
        # Construir log
        log_lines = [
            "=== LOG DE CARGA HISTÓRICO ===",
            f"Archivo: {uploaded_hist.name}",
            f"Filas procesadas: {result['stats'].get('filas_procesadas', 0)}",
            f"Filas insertadas: {result['stats'].get('filas_insertadas', 0)}",
            f"Filas omitidas: {result['stats'].get('filas_omitidas', 0)}",
            f"Semanas únicas: {result['stats'].get('semanas_unicas', 0)}",
            ""
        ]
        
        if result.get('logs'):
            log_lines.append("=== DETALLES DE OMISIONES ===")
            log_lines.extend(result['logs'])
            log_lines.append("")
        
        if result.get('errors'):
            log_lines.append("=== ERRORES ===")
            log_lines.extend(result['errors'])
            log_lines.append("")
        
        log_content = '\n'.join(str(line) for line in log_lines)
        log_filename = f"log_historico_{uploaded_hist.name.replace('.xlsx', '').replace('.xls', '')}.txt"
        
        st.download_button(
            label="📥 Descargar log de carga",
            data=log_content,
            file_name=log_filename,
            mime="text/plain",
            key="download_log_historico_module"
        )
        
        if result['success']:
            st.success("✅ Histórico cargado exitosamente!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Filas procesadas", result['stats']['filas_procesadas'])
            col2.metric("Filas insertadas", result['stats']['filas_insertadas'])
            col3.metric("Semanas únicas", result['stats']['semanas_unicas'])
            
            if result['stats']['filas_omitidas'] > 0:
                st.warning(f"⚠️ {result['stats']['filas_omitidas']} filas omitidas (datos incompletos)")
            
            st.rerun()
        else:
            st.error("❌ Error al cargar histórico")
            for error in result['errors']:
                st.error(f"• {error}")
