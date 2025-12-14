-- ============================================
-- SCRIPT DE INICIALIZACIÓN DE BASE DE DATOS
-- Base de datos: integra_rls
-- ============================================

-- NOTA: Este script debe ejecutarse como usuario postgres
-- Comando: psql -U postgres -f init_db.sql

-- ============================================
-- 1. CREAR BASE DE DATOS
-- ============================================

-- Desconectar usuarios activos (si existe la BD)
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'integra_rls' AND pid != pg_backend_pid();

-- Eliminar BD si existe (CUIDADO: esto borra todos los datos)
DROP DATABASE IF EXISTS integra_rls;

-- Crear nueva base de datos
-- NOTA: Usando template0 para poder especificar collation personalizada
CREATE DATABASE integra_rls
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    TEMPLATE = template0
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE integra_rls IS 'Base de datos para Integra SpA con Row-Level Security';

-- Conectar a la nueva base de datos
\c integra_rls

-- ============================================
-- 2. EJECUTAR SCHEMA
-- ============================================
\echo '================================================'
\echo 'Creando schema y tablas...'
\echo '================================================'
\i schema.sql

-- ============================================
-- 3. CARGAR DATOS DE PRUEBA
-- ============================================
\echo '================================================'
\echo 'Cargando datos de prueba...'
\echo '================================================'
\i seed_data.sql

-- ============================================
-- 4. VERIFICACIÓN FINAL
-- ============================================
\echo '================================================'
\echo 'Verificación de instalación:'
\echo '================================================'

-- Listar tablas
\dt

-- Mostrar resumen de datos
\echo ''
\echo 'Resumen de datos creados:'
SELECT 
    (SELECT COUNT(*) FROM empresas) as empresas,
    (SELECT COUNT(*) FROM usuarios) as usuarios,
    (SELECT COUNT(*) FROM establecimientos) as establecimientos,
    (SELECT COUNT(*) FROM datos_semanales) as datos_semanales,
    (SELECT COUNT(*) FROM datos_diarios) as datos_diarios,
    (SELECT COUNT(*) FROM historico_mdat) as historico_mdat;

\echo ''
\echo 'Usuarios de prueba (password: test123 o admin123):'
SELECT username, nombre_completo, is_admin, activo FROM usuarios ORDER BY id;

\echo ''
\echo 'Relaciones Usuario-Empresa:'
SELECT 
    u.username,
    e.nombre as empresa
FROM usuario_empresa ue
JOIN usuarios u ON ue.usuario_id = u.id
JOIN empresas e ON ue.empresa_id = e.id
ORDER BY u.username, e.nombre;

\echo ''
\echo '================================================'
\echo 'Instalación completada exitosamente!'
\echo '================================================'
\echo ''
\echo 'Para probar RLS desde psql:'
\echo '  SELECT set_user_context(1, false);  -- user_alpha'
\echo '  SELECT * FROM datos_diarios LIMIT 10;'
\echo ''
