-- Agregar columna superficie_pradera a datos_semanales si no existe
ALTER TABLE datos_semanales 
ADD COLUMN IF NOT EXISTS superficie_pradera DECIMAL(10,2);

-- Commit
COMMIT;
