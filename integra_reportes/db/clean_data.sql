-- =============================================
-- LIMPIEZA CONTROLADA DE DATOS (SIN DROPEAR SCHEMA)
-- Uso: psql -U postgres -d integra_rls -f clean_data.sql
-- Objetivo: Dejar la base lista para nueva carga semanal/histórica.
-- =============================================

-- 1. Deshabilitar constraints temporariamente (opcional)
-- (No requerido si usamos TRUNCATE CASCADE en orden correcto)

-- 2. Truncar tablas de datos dependientes
TRUNCATE TABLE datos_diarios RESTART IDENTITY CASCADE;
TRUNCATE TABLE datos_semanales RESTART IDENTITY CASCADE;
TRUNCATE TABLE historico_mdat RESTART IDENTITY CASCADE;

-- 3. Truncar logs (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='upload_logs') THEN
        EXECUTE 'TRUNCATE TABLE upload_logs RESTART IDENTITY CASCADE;';
    END IF;
END;$$;

-- 4. (Opcional) Limpiar establecimientos manteniendo empresas y usuarios
-- Descomentar si se requiere borrar establecimientos
-- TRUNCATE TABLE establecimientos RESTART IDENTITY CASCADE;

-- 5. (Opcional) Limpiar relación usuario_empresa
-- TRUNCATE TABLE usuario_empresa RESTART IDENTITY CASCADE;

-- 6. Verificación rápida
SELECT 
    (SELECT COUNT(*) FROM datos_semanales) AS datos_semanales,
    (SELECT COUNT(*) FROM datos_diarios) AS datos_diarios,
    (SELECT COUNT(*) FROM historico_mdat) AS historico_mdat,
    (SELECT COUNT(*) FROM establecimientos) AS establecimientos,
    (SELECT COUNT(*) FROM empresas) AS empresas;

-- =============================================
-- Fin limpieza
-- =============================================
