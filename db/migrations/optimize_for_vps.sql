-- =====================================================
-- MIGRACIÓN: Optimización de Base de Datos para VPS
-- Fecha: 2026-01-07
-- Descripción: Índices adicionales, tablas faltantes, auditoría
-- =====================================================

-- =====================================================
-- 1. ÍNDICES COMPUESTOS PARA QUERIES FRECUENTES
-- =====================================================

-- Índice para búsquedas empresa + fecha (reportes diarios)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_datos_diarios_empresa_fecha 
    ON datos_diarios(empresa_id, fecha DESC);

-- Índice para búsquedas empresa + período (ranking semanal)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_datos_semanales_empresa_periodo 
    ON datos_semanales(empresa_id, anio DESC, semana DESC);

-- Índice para histórico MDAT (cálculos MDAT 4 sem y 52 sem)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_historico_mdat_empresa_periodo 
    ON historico_mdat(empresa_id, anio DESC, semana DESC);

-- Índice para establecimiento + período (común en JOINs)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_datos_semanales_est_periodo
    ON datos_semanales(establecimiento_id, anio DESC, semana DESC);

-- Índice parcial para usuarios activos (filtro muy común)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usuarios_activos 
    ON usuarios(id) WHERE activo = true;

-- Índice para búsqueda de conceptos (datos diarios)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_datos_diarios_concepto 
    ON datos_diarios(concepto);

-- =====================================================
-- 2. TABLA DE LOGS DE CARGA (si no existe)
-- =====================================================

CREATE TABLE IF NOT EXISTS upload_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_archivo VARCHAR(50),
    nombre_archivo VARCHAR(255),
    registros_procesados INTEGER DEFAULT 0,
    registros_omitidos INTEGER DEFAULT 0,
    estado VARCHAR(50) DEFAULT 'pendiente',
    mensaje TEXT,
    duracion_segundos DECIMAL(10,2),
    detalles_json JSONB
);

-- Índices para tabla de logs
CREATE INDEX IF NOT EXISTS idx_upload_logs_fecha 
    ON upload_logs(fecha_carga DESC);
CREATE INDEX IF NOT EXISTS idx_upload_logs_usuario 
    ON upload_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_upload_logs_estado 
    ON upload_logs(estado);

COMMENT ON TABLE upload_logs IS 'Registro de cargas de archivos Excel al sistema';

-- =====================================================
-- 3. COLUMNAS DE AUDITORÍA
-- =====================================================

-- Agregar updated_at a tablas principales
ALTER TABLE datos_semanales 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
    
ALTER TABLE datos_diarios 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE empresas 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE establecimientos 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE usuarios 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
    
ALTER TABLE usuarios 
    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- =====================================================
-- 4. TRIGGERS PARA UPDATED_AT AUTOMÁTICO
-- =====================================================

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para cada tabla
DROP TRIGGER IF EXISTS trg_datos_semanales_updated ON datos_semanales;
CREATE TRIGGER trg_datos_semanales_updated
    BEFORE UPDATE ON datos_semanales
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_datos_diarios_updated ON datos_diarios;
CREATE TRIGGER trg_datos_diarios_updated
    BEFORE UPDATE ON datos_diarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_empresas_updated ON empresas;
CREATE TRIGGER trg_empresas_updated
    BEFORE UPDATE ON empresas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_establecimientos_updated ON establecimientos;
CREATE TRIGGER trg_establecimientos_updated
    BEFORE UPDATE ON establecimientos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_usuarios_updated ON usuarios;
CREATE TRIGGER trg_usuarios_updated
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 5. TABLA DE SESIONES (para tracking de actividad)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_sessions_usuario ON user_sessions(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active) WHERE is_active = true;

COMMENT ON TABLE user_sessions IS 'Sesiones activas de usuarios para tracking y seguridad';

-- =====================================================
-- 6. TABLA DE DATOS HISTÓRICOS (si no existe)
-- =====================================================

CREATE TABLE IF NOT EXISTS datos_historicos (
    id SERIAL PRIMARY KEY,
    establecimiento VARCHAR(255) NOT NULL,
    establecimiento_id INTEGER REFERENCES establecimientos(id) ON DELETE SET NULL,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    semana INTEGER NOT NULL,
    anio INTEGER,
    fecha DATE,
    vacas_en_ordena INTEGER,
    produccion_total DECIMAL(15,2),
    precio_leche DECIMAL(10,2),
    mdat DECIMAL(10,2),
    porcentaje_grasa DECIMAL(5,2),
    porcentaje_proteina DECIMAL(5,2),
    -- Campos adicionales para compatibilidad
    vacas_masa INTEGER,
    carga_animal DECIMAL(10,2),
    concentrado DECIMAL(10,2),
    forrajes_conservados DECIMAL(10,2),
    praderas_otros_verdes DECIMAL(10,2),
    total_ms DECIMAL(10,2),
    costo_racion_vaca DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Constraint para evitar duplicados
    UNIQUE(establecimiento, semana, COALESCE(anio, EXTRACT(YEAR FROM fecha)::INTEGER))
);

-- Índices para datos históricos
CREATE INDEX IF NOT EXISTS idx_datos_historicos_establecimiento 
    ON datos_historicos(establecimiento);
CREATE INDEX IF NOT EXISTS idx_datos_historicos_semana 
    ON datos_historicos(semana, anio);
CREATE INDEX IF NOT EXISTS idx_datos_historicos_fecha 
    ON datos_historicos(fecha);
CREATE INDEX IF NOT EXISTS idx_datos_historicos_empresa 
    ON datos_historicos(empresa_id);

COMMENT ON TABLE datos_historicos IS 'Histórico completo de datos semanales para análisis y cálculos MDAT';

-- =====================================================
-- 7. ESTADÍSTICAS Y VACUUM
-- =====================================================

-- Actualizar estadísticas de todas las tablas
ANALYZE empresas;
ANALYZE establecimientos;
ANALYZE usuarios;
ANALYZE usuario_empresa;
ANALYZE datos_semanales;
ANALYZE datos_diarios;
ANALYZE historico_mdat;

-- =====================================================
-- 8. VERIFICACIÓN
-- =====================================================

-- Mostrar índices creados
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Mostrar tamaño de tablas
SELECT 
    relname as tabla,
    pg_size_pretty(pg_total_relation_size(relid)) as tamaño_total,
    pg_size_pretty(pg_relation_size(relid)) as tamaño_datos,
    n_live_tup as filas_aprox
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
