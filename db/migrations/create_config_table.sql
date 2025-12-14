-- Crear tabla de configuración de la aplicación
CREATE TABLE IF NOT EXISTS configuracion_app (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES usuarios(id)
);

-- Insertar configuración inicial
INSERT INTO configuracion_app (clave, valor) VALUES
('filtros_defecto', '[]'),
('nota_semanal', ''),
('nota_semanal_visible', 'true')
ON CONFLICT (clave) DO NOTHING;
