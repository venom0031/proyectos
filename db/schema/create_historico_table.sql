-- ============================================
-- TABLA HISTÓRICO COMPLETO
-- Almacena todos los datos semanales históricos
-- ============================================

-- Eliminar tabla anterior si existe
DROP TABLE IF EXISTS datos_historicos CASCADE;

-- Crear tabla de histórico completo
CREATE TABLE datos_historicos (
    id SERIAL PRIMARY KEY,
    
    -- Identificadores
    semana INTEGER NOT NULL,
    fecha DATE NOT NULL,  -- Fecha de cierre del período
    empresa VARCHAR(255) NOT NULL,
    establecimiento VARCHAR(255),  -- Puede ser NULL para datos agregados de empresa
    
    -- Datos de producción
    vacas_en_produccion INTEGER,
    leche_enviada DECIMAL(15,2),
    leche_no_vendible DECIMAL(15,2),
    pna_terneros DECIMAL(15,2),
    produccion_total DECIMAL(15,2),
    precio_leche DECIMAL(10,2),
    dias_lactancia INTEGER,
    
    -- Calidad
    porcentaje_grasa DECIMAL(5,2),
    porcentaje_proteina DECIMAL(5,2),
    
    -- Materia seca
    kg_ms_pradera DECIMAL(10,2),
    kg_ms_conservado DECIMAL(10,2),
    kg_ms_concentrado DECIMAL(10,2),
    consumo_ms DECIMAL(10,2),
    ms_por_ha DECIMAL(10,2),
    
    -- Costos
    costo_racion_vaca DECIMAL(10,2),
    
    -- Indicadores calculados
    mdat DECIMAL(12,2),
    eficiencia DECIMAL(8,4),
    
    -- Vacas
    vacas_masa INTEGER,
    vacas_en_ordena INTEGER,
    relacion_ordena_masa DECIMAL(5,2),
    
    -- Superficie
    superficie_praderas DECIMAL(10,2),
    
    -- Otros
    porcentaje_leche_no_vendible DECIMAL(5,2),
    carga_animal DECIMAL(10,2),
    
    -- Metadatos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint único: una fila por semana/empresa/establecimiento
    UNIQUE(semana, fecha, empresa, establecimiento)
);

-- Índices para performance
CREATE INDEX idx_historico_semana ON datos_historicos(semana);
CREATE INDEX idx_historico_fecha ON datos_historicos(fecha);
CREATE INDEX idx_historico_empresa ON datos_historicos(empresa);
CREATE INDEX idx_historico_establecimiento ON datos_historicos(establecimiento);
CREATE INDEX idx_historico_fecha_empresa ON datos_historicos(fecha, empresa);

-- Comentarios
COMMENT ON TABLE datos_historicos IS 'Histórico completo de datos semanales para análisis y comparativos';
COMMENT ON COLUMN datos_historicos.semana IS 'Número de semana del año';
COMMENT ON COLUMN datos_historicos.fecha IS 'Fecha de cierre del período semanal';
COMMENT ON COLUMN datos_historicos.mdat IS 'Margen Directo de Alimentación Total';
