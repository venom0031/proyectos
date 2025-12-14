-- Migration: Add theme configuration columns to empresas table
-- Run this migration to enable company-specific colors and logos

-- Add color_primario column for company accent color
ALTER TABLE empresas 
ADD COLUMN IF NOT EXISTS color_primario VARCHAR(7) DEFAULT NULL;

-- Add logo_url column for company logo
ALTER TABLE empresas 
ADD COLUMN IF NOT EXISTS logo_url TEXT DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN empresas.color_primario IS 'Color primario hex (#RRGGBB) para personalizar tema de la empresa';
COMMENT ON COLUMN empresas.logo_url IS 'URL del logo de la empresa para mostrar en sidebar';

-- Insert default theme config if not exists
INSERT INTO configuracion_app (clave, valor, updated_at)
VALUES ('tema_defecto', 'light', CURRENT_TIMESTAMP)
ON CONFLICT (clave) DO NOTHING;
