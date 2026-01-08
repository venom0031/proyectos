-- =====================================================
-- MIGRACIÓN: Configuración de Mantenimiento Automático
-- Para ejecutar en el VPS como usuario postgres
-- =====================================================

-- =====================================================
-- 1. CONFIGURACIÓN DE AUTOVACUUM (recomendado para producción)
-- =====================================================

-- Estas son configuraciones a nivel de tabla
-- Para configuración global, editar postgresql.conf

-- Tablas grandes: vacuum más frecuente
ALTER TABLE datos_diarios SET (
    autovacuum_vacuum_scale_factor = 0.05,  -- 5% en vez de 20%
    autovacuum_analyze_scale_factor = 0.02,  -- 2% en vez de 10%
    autovacuum_vacuum_cost_delay = 10        -- más agresivo
);

ALTER TABLE datos_semanales SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE datos_historicos SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- =====================================================
-- 2. FUNCIÓN PARA LIMPIEZA DE SESIONES EXPIRADAS
-- =====================================================

CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP 
       OR (is_active = false AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Sesiones expiradas eliminadas: %', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 3. FUNCIÓN PARA LIMPIEZA DE LOGS ANTIGUOS
-- =====================================================

CREATE OR REPLACE FUNCTION cleanup_old_logs(dias_retener INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM upload_logs 
    WHERE fecha_carga < CURRENT_TIMESTAMP - (dias_retener || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Logs antiguos eliminados: % (retención: % días)', deleted_count, dias_retener;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 4. FUNCIÓN DE MANTENIMIENTO GENERAL
-- =====================================================

CREATE OR REPLACE FUNCTION run_maintenance()
RETURNS TABLE (
    tarea TEXT,
    resultado TEXT,
    duracion INTERVAL
) AS $$
DECLARE
    start_time TIMESTAMP;
    task_start TIMESTAMP;
    sessions_cleaned INTEGER;
    logs_cleaned INTEGER;
BEGIN
    start_time := clock_timestamp();
    
    -- Limpiar sesiones
    task_start := clock_timestamp();
    SELECT cleanup_expired_sessions() INTO sessions_cleaned;
    RETURN QUERY SELECT 
        'Limpieza de sesiones'::TEXT,
        sessions_cleaned || ' eliminadas'::TEXT,
        clock_timestamp() - task_start;
    
    -- Limpiar logs
    task_start := clock_timestamp();
    SELECT cleanup_old_logs(90) INTO logs_cleaned;
    RETURN QUERY SELECT 
        'Limpieza de logs'::TEXT,
        logs_cleaned || ' eliminados'::TEXT,
        clock_timestamp() - task_start;
    
    -- Actualizar estadísticas
    task_start := clock_timestamp();
    ANALYZE datos_semanales;
    ANALYZE datos_diarios;
    ANALYZE datos_historicos;
    RETURN QUERY SELECT 
        'ANALYZE tablas principales'::TEXT,
        'Completado'::TEXT,
        clock_timestamp() - task_start;
    
    -- Resumen
    RETURN QUERY SELECT 
        'TOTAL'::TEXT,
        'Mantenimiento completado'::TEXT,
        clock_timestamp() - start_time;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION run_maintenance() IS 'Ejecuta tareas de mantenimiento: limpieza de sesiones, logs y actualización de estadísticas';

-- =====================================================
-- 5. VISTA DE SALUD DE LA BASE DE DATOS
-- =====================================================

CREATE OR REPLACE VIEW v_database_health AS
SELECT 
    -- Tamaño de BD
    pg_size_pretty(pg_database_size(current_database())) as db_size,
    
    -- Conexiones
    (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as conexiones_activas,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_conexiones,
    
    -- Tablas más grandes
    (SELECT jsonb_agg(jsonb_build_object(
        'tabla', relname,
        'tamaño', pg_size_pretty(pg_total_relation_size(relid)),
        'filas', n_live_tup
    ) ORDER BY pg_total_relation_size(relid) DESC)
    FROM pg_stat_user_tables
    LIMIT 5) as top_5_tablas,
    
    -- Cache hit ratio (debería ser > 99%)
    ROUND(
        (SELECT sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100
         FROM pg_statio_user_tables), 2
    ) as cache_hit_ratio,
    
    -- Último vacuum
    (SELECT max(last_vacuum) FROM pg_stat_user_tables) as ultimo_vacuum,
    (SELECT max(last_analyze) FROM pg_stat_user_tables) as ultimo_analyze,
    
    -- Timestamp
    CURRENT_TIMESTAMP as checked_at;

COMMENT ON VIEW v_database_health IS 'Vista de salud y métricas de la base de datos';

-- =====================================================
-- 6. VISTA DE RESUMEN DE DATOS
-- =====================================================

CREATE OR REPLACE VIEW v_data_summary AS
SELECT 
    (SELECT count(*) FROM empresas) as total_empresas,
    (SELECT count(*) FROM establecimientos) as total_establecimientos,
    (SELECT count(*) FROM usuarios WHERE activo = true) as usuarios_activos,
    (SELECT count(*) FROM datos_semanales) as registros_semanales,
    (SELECT count(*) FROM datos_diarios) as registros_diarios,
    (SELECT count(*) FROM datos_historicos) as registros_historicos,
    (SELECT max(anio * 100 + semana) FROM datos_semanales) as ultima_semana,
    (SELECT max(fecha) FROM datos_diarios) as ultima_fecha_diaria,
    CURRENT_TIMESTAMP as checked_at;

COMMENT ON VIEW v_data_summary IS 'Resumen de datos cargados en el sistema';

-- =====================================================
-- 7. PERMISOS (ajustar según necesidad)
-- =====================================================

-- Crear rol de solo lectura para reportes
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user NOLOGIN;
    END IF;
END
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- =====================================================
-- INSTRUCCIONES DE USO
-- =====================================================

/*
Para ejecutar mantenimiento manual:
    SELECT * FROM run_maintenance();

Para ver salud de la BD:
    SELECT * FROM v_database_health;

Para ver resumen de datos:
    SELECT * FROM v_data_summary;

Configurar cron job para mantenimiento automático:
    0 4 * * * psql -U postgres -d integra_rls -c "SELECT run_maintenance();" >> /var/log/integra-maintenance.log 2>&1
*/
