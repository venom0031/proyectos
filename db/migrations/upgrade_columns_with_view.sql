-- 1. Eliminar la vista que depende de las columnas
DROP VIEW IF EXISTS v_ranking_semanal;

-- 2. Alterar las columnas para permitir valores grandes
ALTER TABLE datos_semanales
  ALTER COLUMN costo_racion_vaca TYPE DECIMAL(15,2),
  ALTER COLUMN mdat_litros_vaca_dia TYPE DECIMAL(15,2),
  ALTER COLUMN mdat TYPE DECIMAL(15,2),
  ALTER COLUMN precio_leche TYPE DECIMAL(15,2),
  ALTER COLUMN costo_promedio_concentrado TYPE DECIMAL(15,2),
  ALTER COLUMN produccion_promedio TYPE DECIMAL(15,2),
  ALTER COLUMN kg_ms_concentrado_vaca TYPE DECIMAL(15,2),
  ALTER COLUMN kg_ms_conservado_vaca TYPE DECIMAL(15,2),
  ALTER COLUMN praderas_otros_verdes TYPE DECIMAL(15,2),
  ALTER COLUMN total_ms TYPE DECIMAL(15,2);

-- 3. Vuelve a crear la vista
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
