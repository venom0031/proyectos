-- ============================================
-- SCHEMA PRINCIPAL PARA INTEGRA RLS
-- Base de datos: integra_rls
-- ============================================

-- ============================================
-- 1. EXTENSIONES
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 2. TABLAS PRINCIPALES
-- ============================================

-- Tabla de Empresas
CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    codigo VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Establecimientos (cada uno pertenece a una empresa)
CREATE TABLE establecimientos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    superficie_praderas DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nombre, empresa_id)
);

-- Tabla de Usuarios
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(255),
    email VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relación Usuario-Empresa (N:M)
CREATE TABLE usuario_empresa (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, empresa_id)
);

-- Tabla de Datos Semanales (para Ranking Semanal - SIN RLS, público)
CREATE TABLE datos_semanales (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES establecimientos(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    semana INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    
    -- Datos de la matriz
    vacas_masa INTEGER,
    vacas_en_ordena INTEGER,
    carga_animal DECIMAL(10,2),
    porcentaje_grasa DECIMAL(5,2),
    proteinas DECIMAL(5,2),
    costo_promedio_concentrado DECIMAL(10,2),
    grms_concentrado_por_litro INTEGER,
    kg_ms_concentrado_vaca DECIMAL(10,2),
    kg_ms_conservado_vaca DECIMAL(10,2),
    praderas_otros_verdes DECIMAL(10,2),
    total_ms DECIMAL(10,2),
    produccion_promedio DECIMAL(10,2),
    costo_racion_vaca DECIMAL(10,2),
    precio_leche DECIMAL(10,2),
    mdat_litros_vaca_dia DECIMAL(10,2),
    porcentaje_costo_alimentos DECIMAL(5,2),
    mdat DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(establecimiento_id, semana, anio)
);

-- Tabla de Datos Diarios (para Detalle Diario - CON RLS por empresa)
CREATE TABLE datos_diarios (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES establecimientos(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    categoria VARCHAR(100),
    concepto VARCHAR(255) NOT NULL,
    valor DECIMAL(15,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(establecimiento_id, fecha, concepto)
);

-- Tabla de Histórico MDAT (para comparativos 4 sem y 52 sem)
CREATE TABLE historico_mdat (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES establecimientos(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    semana INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    mdat DECIMAL(10,2),
    vacas_en_ordena INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(establecimiento_id, semana, anio)
);

-- ============================================
-- 3. ÍNDICES PARA PERFORMANCE
-- ============================================
CREATE INDEX idx_establecimientos_empresa ON establecimientos(empresa_id);
CREATE INDEX idx_usuario_empresa_usuario ON usuario_empresa(usuario_id);
CREATE INDEX idx_usuario_empresa_empresa ON usuario_empresa(empresa_id);
CREATE INDEX idx_datos_semanales_establecimiento ON datos_semanales(establecimiento_id);
CREATE INDEX idx_datos_semanales_empresa ON datos_semanales(empresa_id);
CREATE INDEX idx_datos_semanales_semana ON datos_semanales(semana, anio);
CREATE INDEX idx_datos_diarios_establecimiento ON datos_diarios(establecimiento_id);
CREATE INDEX idx_datos_diarios_empresa ON datos_diarios(empresa_id);
CREATE INDEX idx_datos_diarios_fecha ON datos_diarios(fecha);
CREATE INDEX idx_historico_mdat_establecimiento ON historico_mdat(establecimiento_id);
CREATE INDEX idx_historico_mdat_semana ON historico_mdat(semana, anio);

-- ============================================
-- 4. ROW-LEVEL SECURITY (RLS)
-- ============================================

-- Habilitar RLS en las tablas que lo necesitan
ALTER TABLE establecimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE datos_diarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_mdat ENABLE ROW LEVEL SECURITY;

-- IMPORTANTE: datos_semanales NO tiene RLS (ranking visible para todos)

-- ============================================
-- 5. POLÍTICAS RLS
-- ============================================

-- Política para establecimientos: solo ver los de las empresas del usuario
CREATE POLICY establecimientos_user_policy ON establecimientos
    FOR SELECT
    USING (
        empresa_id IN (
            SELECT empresa_id 
            FROM usuario_empresa 
            WHERE usuario_id = current_setting('app.current_user_id', true)::integer
        )
        OR current_setting('app.is_admin', true)::boolean = true
    );

-- Política para datos_diarios: solo ver datos de las empresas del usuario
CREATE POLICY datos_diarios_user_policy ON datos_diarios
    FOR SELECT
    USING (
        empresa_id IN (
            SELECT empresa_id 
            FROM usuario_empresa 
            WHERE usuario_id = current_setting('app.current_user_id', true)::integer
        )
        OR current_setting('app.is_admin', true)::boolean = true
    );

-- Política para historico_mdat: solo ver histórico de las empresas del usuario
CREATE POLICY historico_mdat_user_policy ON historico_mdat
    FOR SELECT
    USING (
        empresa_id IN (
            SELECT empresa_id 
            FROM usuario_empresa 
            WHERE usuario_id = current_setting('app.current_user_id', true)::integer
        )
        OR current_setting('app.is_admin', true)::boolean = true
    );

-- ============================================
-- 6. FUNCIONES AUXILIARES
-- ============================================

-- Función para establecer el contexto de usuario (llamada desde Python)
CREATE OR REPLACE FUNCTION set_user_context(p_user_id INTEGER, p_is_admin BOOLEAN)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_user_id', p_user_id::text, false);
    PERFORM set_config('app.is_admin', p_is_admin::text, false);
END;
$$ LANGUAGE plpgsql;

-- Función helper para hash de passwords (bcrypt)
CREATE OR REPLACE FUNCTION hash_password(password TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN crypt(password, gen_salt('bf', 10));
END;
$$ LANGUAGE plpgsql;

-- Función para verificar password
CREATE OR REPLACE FUNCTION verify_password(password TEXT, password_hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN password_hash = crypt(password, password_hash);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 7. VISTAS AUXILIARES
-- ============================================

-- Vista de ranking semanal (todas las empresas, sin RLS)
CREATE OR REPLACE VIEW v_ranking_semanal AS
SELECT 
    e.nombre as establecimiento,
    emp.nombre as empresa,
    ds.semana,
    ds.anio,
    ds.vacas_masa,
    ds.vacas_en_ordena,
    ds.carga_animal,
    ds.porcentaje_grasa,
    ds.proteinas,
    ds.costo_promedio_concentrado,
    ds.grms_concentrado_por_litro,
    ds.kg_ms_concentrado_vaca,
    ds.kg_ms_conservado_vaca,
    ds.praderas_otros_verdes,
    ds.total_ms,
    ds.produccion_promedio,
    ds.costo_racion_vaca,
    ds.precio_leche,
    ds.mdat_litros_vaca_dia,
    ds.porcentaje_costo_alimentos,
    ds.mdat,
    RANK() OVER (ORDER BY ds.mdat DESC NULLS LAST) as ranking_mdat
FROM datos_semanales ds
JOIN establecimientos e ON ds.establecimiento_id = e.id
JOIN empresas emp ON ds.empresa_id = emp.id;

-- Vista de detalle diario (CON RLS aplicado)
CREATE OR REPLACE VIEW v_detalle_diario AS
SELECT 
    e.nombre as establecimiento,
    emp.nombre as empresa,
    dd.fecha,
    dd.categoria,
    dd.concepto,
    dd.valor,
    dd.empresa_id
FROM datos_diarios dd
JOIN establecimientos e ON dd.establecimiento_id = e.id
JOIN empresas emp ON dd.empresa_id = emp.id;

-- Habilitar RLS en la vista de detalle diario
ALTER VIEW v_detalle_diario SET (security_barrier = true);

-- ============================================
-- COMENTARIOS
-- ============================================
COMMENT ON TABLE empresas IS 'Empresas del sistema (ej: Empresa Alpha, Beta, Gamma)';
COMMENT ON TABLE establecimientos IS 'Establecimientos ganaderos asociados a empresas';
COMMENT ON TABLE usuarios IS 'Usuarios del sistema con autenticación';
COMMENT ON TABLE usuario_empresa IS 'Relación N:M entre usuarios y empresas para RLS';
COMMENT ON TABLE datos_semanales IS 'Datos semanales para Ranking - SIN RLS (público)';
COMMENT ON TABLE datos_diarios IS 'Datos diarios para Detalle - CON RLS (filtrado por empresa)';
COMMENT ON TABLE historico_mdat IS 'Histórico MDAT para comparativos 4 sem y 52 sem';
