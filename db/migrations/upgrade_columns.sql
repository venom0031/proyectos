-- Ampliar precisión de columnas numéricas para aceptar valores grandes
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

-- Opcional: ampliar también en historico_mdat si es necesario
ALTER TABLE historico_mdat
  ALTER COLUMN mdat TYPE DECIMAL(15,2);
