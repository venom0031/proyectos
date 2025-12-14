-- Agregar columnas de período a datos_semanales
ALTER TABLE datos_semanales 
ADD COLUMN fecha_inicio DATE,
ADD COLUMN fecha_fin DATE;

-- Crear índice por rango de fechas para búsquedas rápidas
CREATE INDEX idx_datos_semanales_periodo ON datos_semanales(fecha_inicio, fecha_fin);

-- Actualizar la constraint UNIQUE para usar las nuevas fechas en lugar de semana/anio
-- Primero eliminamos el UNIQUE anterior
ALTER TABLE datos_semanales 
DROP CONSTRAINT IF EXISTS datos_semanales_establecimiento_semana_anio_key;

-- Agregamos el nuevo UNIQUE basado en período
ALTER TABLE datos_semanales 
ADD CONSTRAINT datos_semanales_establecimiento_periodo_key 
UNIQUE(establecimiento_id, fecha_inicio, fecha_fin);

-- Opcionalmente, mantener semana/anio para compatibilidad histórica (pero no obligatorio)
