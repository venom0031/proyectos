-- Script para renombrar columnas "año" a "anio" evitando problemas de encoding

-- Renombrar en datos_semanales
ALTER TABLE datos_semanales RENAME COLUMN "año" TO anio;

-- Renombrar en historico_mdat  
ALTER TABLE historico_mdat RENAME COLUMN "año" TO anio;

-- Verificar que se aplicó
SELECT 'Columnas renombradas exitosamente' AS resultado;
