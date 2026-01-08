# =====================================================
# MÓDULO: Visualización de Logs
# =====================================================
"""
Funciones para visualizar logs del sistema en el admin panel.
"""

import streamlit as st
import pandas as pd

from db_connection import execute_query, execute_update


def render_logs_tab():
    """Renderiza la pestaña de logs del sistema."""
    st.header("📊 Logs del Sistema")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        tipo_filter = st.multiselect(
            "Tipo de Archivo", 
            ["semanal", "historico", "historico_completo"], 
            default=["semanal", "historico"]
        )
    with col2:
        estado_filter = st.multiselect(
            "Estado", 
            ["exito", "error", "warning"], 
            default=["exito", "error", "warning"]
        )
    
    # Query logs
    logs = _get_logs()
    
    if logs and len(logs) > 0:
        df_logs = pd.DataFrame(logs)
        
        # Formatear fecha
        df_logs['fecha_carga'] = pd.to_datetime(df_logs['fecha_carga']).dt.strftime('%d-%m-%Y %H:%M')
        
        # Filtrar
        if tipo_filter:
            df_logs = df_logs[df_logs['tipo_archivo'].isin(tipo_filter)]
        if estado_filter:
            df_logs = df_logs[df_logs['estado'].isin(estado_filter)]
        
        # Mapear iconos
        df_logs['Estado'] = df_logs['estado'].map({
            'exito': '✅',
            'error': '❌',
            'warning': '⚠️'
        }).fillna('❓')
        
        st.dataframe(
            df_logs[['fecha_carga', 'username', 'tipo_archivo', 'nombre_archivo', 
                     'registros_procesados', 'Estado', 'mensaje']],
            use_container_width=True,
            hide_index=True
        )
        
        # Estadísticas
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total registros", len(df_logs))
        col2.metric("Exitosos", len(df_logs[df_logs['estado'] == 'exito']))
        col3.metric("Errores", len(df_logs[df_logs['estado'] == 'error']))
    else:
        st.info("No hay registros de actividad")


def _get_logs():
    """Obtiene los logs de la base de datos, creando la tabla si no existe."""
    query = """
        SELECT l.id, l.fecha_carga, u.username, l.tipo_archivo, l.nombre_archivo, 
               l.registros_procesados, l.registros_omitidos, l.estado, l.mensaje
        FROM upload_logs l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        ORDER BY l.fecha_carga DESC
        LIMIT 100
    """
    
    try:
        return execute_query(query)
    except Exception as e:
        if 'upload_logs' in str(e):
            st.warning("Tabla 'upload_logs' no existe. Creándola...")
            try:
                execute_update("""
                    CREATE TABLE IF NOT EXISTS upload_logs (
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
                return []
            except Exception as ddl_err:
                st.error(f"No se pudo crear tabla 'upload_logs': {ddl_err}")
                return []
        else:
            st.error(f"Error obteniendo logs: {e}")
            return []
