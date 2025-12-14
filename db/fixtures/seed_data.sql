-- ============================================
-- DATOS DE PRUEBA PARA INTEGRA RLS
-- ============================================

-- ============================================
-- 1. EMPRESAS
-- ============================================
INSERT INTO empresas (nombre, codigo) VALUES
    ('Empresa Alpha', 'ALPHA'),
    ('Empresa Beta', 'BETA'),
    ('Empresa Gamma', 'GAMMA');

-- ============================================
-- 2. USUARIOS (password para todos: "test123")
-- ============================================
INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo) VALUES
    ('user_alpha', hash_password('test123'), 'Usuario Alpha', 'alpha@integra.cl', false, true),
    ('user_beta', hash_password('test123'), 'Usuario Beta', 'beta@integra.cl', false, true),
    ('admin', hash_password('admin123'), 'Administrador', 'admin@integra.cl', true, true),
    ('user_multi', hash_password('test123'), 'Usuario Multi-Empresa', 'multi@integra.cl', false, true);

-- ============================================
-- 3. RELACIONES USUARIO-EMPRESA
-- ============================================
-- user_alpha solo ve Empresa Alpha
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES
    ((SELECT id FROM usuarios WHERE username = 'user_alpha'), (SELECT id FROM empresas WHERE codigo = 'ALPHA'));

-- user_beta solo ve Empresa Beta
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES
    ((SELECT id FROM usuarios WHERE username = 'user_beta'), (SELECT id FROM empresas WHERE codigo = 'BETA'));

-- user_multi ve Alpha y Gamma
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES
    ((SELECT id FROM usuarios WHERE username = 'user_multi'), (SELECT id FROM empresas WHERE codigo = 'ALPHA')),
    ((SELECT id FROM usuarios WHERE username = 'user_multi'), (SELECT id FROM empresas WHERE codigo = 'GAMMA'));

-- admin no necesita relaciones (is_admin = true en RLS policy)

-- ============================================
-- 4. ESTABLECIMIENTOS
-- ============================================
INSERT INTO establecimientos (nombre, empresa_id, superficie_praderas) VALUES
    -- Establecimientos de Empresa Alpha
    ('Fundo Los Robles', (SELECT id FROM empresas WHERE codigo = 'ALPHA'), 450.50),
    ('Hacienda El Vergel', (SELECT id FROM empresas WHERE codigo = 'ALPHA'), 320.00),
    ('Predio Santa Rosa', (SELECT id FROM empresas WHERE codigo = 'ALPHA'), 280.75),
    
    -- Establecimientos de Empresa Beta
    ('Estancia La Pradera', (SELECT id FROM empresas WHERE codigo = 'BETA'), 520.00),
    ('Fundo San Miguel', (SELECT id FROM empresas WHERE codigo = 'BETA'), 390.25),
    
    -- Establecimientos de Empresa Gamma
    ('Hacienda Los Andes', (SELECT id FROM empresas WHERE codigo = 'GAMMA'), 610.00),
    ('Predio Valle Verde', (SELECT id FROM empresas WHERE codigo = 'GAMMA'), 440.50);

-- ============================================
-- 5. DATOS SEMANALES (Semana 48, Año 2025)
-- ============================================
INSERT INTO datos_semanales (
    establecimiento_id, empresa_id, semana, anio,
    vacas_masa, vacas_en_ordena, carga_animal, porcentaje_grasa, proteinas,
    costo_promedio_concentrado, grms_concentrado_por_litro,
    kg_ms_concentrado_vaca, kg_ms_conservado_vaca, praderas_otros_verdes, total_ms,
    produccion_promedio, costo_racion_vaca, precio_leche, mdat_litros_vaca_dia,
    porcentaje_costo_alimentos, mdat
) VALUES
    -- Fundo Los Robles (Alpha) - Mejor MDAT
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Fundo Los Robles'),
        (SELECT id FROM empresas WHERE codigo = 'ALPHA'),
        48, 2025,
        450, 420, 1.85, 3.95, 3.42,
        285.50, 320,
        6.8, 4.2, 12.5, 23.5,
        32.5, 3850, 385, 28.5,
        42.5, 8950
    ),
    -- Hacienda El Vergel (Alpha)
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Hacienda El Vergel'),
        (SELECT id FROM empresas WHERE codigo = 'ALPHA'),
        48, 2025,
        380, 350, 1.72, 3.88, 3.35,
        290.00, 335,
        7.2, 4.0, 11.8, 23.0,
        30.2, 3920, 378, 26.8,
        44.2, 7650
    ),
    -- Predio Santa Rosa (Alpha)
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Predio Santa Rosa'),
        (SELECT id FROM empresas WHERE codigo = 'ALPHA'),
        48, 2025,
        320, 295, 1.65, 3.80, 3.28,
        295.75, 345,
        7.5, 3.8, 11.2, 22.5,
        28.8, 4050, 370, 25.2,
        46.8, 6890
    ),
    -- Estancia La Pradera (Beta) - MDAT medio
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Estancia La Pradera'),
        (SELECT id FROM empresas WHERE codigo = 'BETA'),
        48, 2025,
        580, 540, 1.95, 4.02, 3.48,
        278.25, 310,
        6.5, 4.5, 13.2, 24.2,
        34.8, 3780, 390, 30.2,
        40.8, 9250
    ),
    -- Fundo San Miguel (Beta)
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Fundo San Miguel'),
        (SELECT id FROM empresas WHERE codigo = 'BETA'),
        48, 2025,
        420, 385, 1.68, 3.85, 3.30,
        288.50, 330,
        7.0, 4.1, 11.5, 22.6,
        29.5, 3950, 375, 26.5,
        45.2, 7280
    ),
    -- Hacienda Los Andes (Gamma) - MDAT alto
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Hacienda Los Andes'),
        (SELECT id FROM empresas WHERE codigo = 'GAMMA'),
        48, 2025,
        680, 630, 2.05, 4.10, 3.55,
        270.00, 295,
        6.2, 4.8, 14.0, 25.0,
        36.5, 3650, 398, 31.8,
        38.5, 10250
    ),
    -- Predio Valle Verde (Gamma)
    (
        (SELECT id FROM establecimientos WHERE nombre = 'Predio Valle Verde'),
        (SELECT id FROM empresas WHERE codigo = 'GAMMA'),
        48, 2025,
        490, 455, 1.78, 3.92, 3.38,
        282.00, 315,
        6.6, 4.3, 12.8, 23.7,
        31.8, 3820, 382, 27.8,
        43.5, 8150
    );

-- ============================================
-- 6. DATOS DIARIOS (últimos 7 días de noviembre 2025)
-- ============================================

-- Función helper para insertar datos diarios de un establecimiento
CREATE OR REPLACE FUNCTION insert_datos_diarios_establecimiento(
    p_establecimiento VARCHAR,
    p_fecha_inicio DATE,
    p_dias INTEGER
) RETURNS VOID AS $$
DECLARE
    v_establecimiento_id INTEGER;
    v_empresa_id INTEGER;
    v_fecha DATE;
    i INTEGER;
    base_produccion DECIMAL;
    variacion DECIMAL;
BEGIN
    -- Obtener IDs
    SELECT e.id, e.empresa_id INTO v_establecimiento_id, v_empresa_id
    FROM establecimientos e
    WHERE e.nombre = p_establecimiento;
    
    -- Producción base aleatoria
    base_produccion := 30 + (random() * 10);
    
    -- Insertar datos para cada día
    FOR i IN 0..(p_dias - 1) LOOP
        v_fecha := p_fecha_inicio + i;
        variacion := -2 + (random() * 4);
        
        -- Producción de leche
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Producción', 'Litros de leche producidos', base_produccion + variacion);
        
        -- Vacas en ordeña
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Inventario', 'Vacas en ordeña', 420 + floor(random() * 20)::integer);
        
        -- Concentrado consumido
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Alimentación', 'Kg concentrado consumido', 2800 + floor(random() * 400)::integer);
        
        -- Forraje conservado
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Alimentación', 'Kg forraje conservado', 1600 + floor(random() * 300)::integer);
        
        -- Costo ración
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Costos', 'Costo ración diaria ($)', 3850 + floor(random() * 300)::integer);
        
        -- Precio leche
        INSERT INTO datos_diarios (establecimiento_id, empresa_id, fecha, categoria, concepto, valor)
        VALUES (v_establecimiento_id, v_empresa_id, v_fecha, 'Ingresos', 'Precio leche ($/L)', 375 + floor(random() * 20)::integer);
        
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Insertar datos diarios para todos los establecimientos
DO $$
DECLARE
    est RECORD;
BEGIN
    FOR est IN SELECT nombre FROM establecimientos LOOP
        PERFORM insert_datos_diarios_establecimiento(est.nombre, '2025-11-24'::DATE, 7);
    END LOOP;
END;
$$;

-- Limpiar función temporal
DROP FUNCTION IF EXISTS insert_datos_diarios_establecimiento;

-- ============================================
-- 7. HISTÓRICO MDAT (últimas 52 semanas)
-- ============================================

-- Insertar histórico para cada establecimiento
DO $$
DECLARE
    est RECORD;
    semana_actual INTEGER := 48;
    año_actual INTEGER := 2025;
    semana INTEGER;
    año INTEGER;
    mdat_base DECIMAL;
    vacas_base INTEGER;
    i INTEGER;
BEGIN
    FOR est IN SELECT id, empresa_id FROM establecimientos LOOP
        -- Valores base aleatorios
        mdat_base := 7000 + (random() * 3000);
        vacas_base := 350 + floor(random() * 150)::integer;
        
        -- Insertar últimas 52 semanas
        FOR i IN 1..52 LOOP
            semana := semana_actual - i;
            año := año_actual;
            
            -- Ajustar año si la semana es negativa
            IF semana <= 0 THEN
                semana := semana + 52;
                año := año - 1;
            END IF;
            
            INSERT INTO historico_mdat (establecimiento_id, empresa_id, semana, anio, mdat, vacas_en_ordena)
            VALUES (
                est.id,
                est.empresa_id,
                semana,
                año,
                mdat_base + (random() * 1000 - 500),
                vacas_base + floor(random() * 50 - 25)::integer
            );
        END LOOP;
    END LOOP;
END;
$$;

-- ============================================
-- VERIFICACIÓN DE DATOS
-- ============================================
SELECT 'Empresas creadas: ' || COUNT(*) FROM empresas;
SELECT 'Usuarios creados: ' || COUNT(*) FROM usuarios;
SELECT 'Establecimientos creados: ' || COUNT(*) FROM establecimientos;
SELECT 'Datos semanales: ' || COUNT(*) FROM datos_semanales;
SELECT 'Datos diarios: ' || COUNT(*) FROM datos_diarios;
SELECT 'Histórico MDAT: ' || COUNT(*) FROM historico_mdat;
