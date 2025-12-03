
-- Tabla para logs de carga
CREATE TABLE IF NOT EXISTS upload_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo_archivo VARCHAR(50) NOT NULL, -- 'semanal', 'historico'
    nombre_archivo VARCHAR(255) NOT NULL,
    fecha_carga TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    registros_procesados INTEGER DEFAULT 0,
    registros_omitidos INTEGER DEFAULT 0,
    estado VARCHAR(20) NOT NULL, -- 'exito', 'error', 'warning'
    mensaje TEXT
);

-- Permisos
GRANT ALL PRIVILEGES ON TABLE upload_logs TO postgres;
GRANT ALL PRIVILEGES ON SEQUENCE upload_logs_id_seq TO postgres;
