-- Script para insertar empresas y establecimientos

-- Agregar constraint UNIQUE a empresas.codigo
ALTER TABLE empresas ADD CONSTRAINT empresas_codigo_unique UNIQUE (codigo);

-- Insertar empresas
INSERT INTO empresas (codigo, nombre) VALUES
('79.964.160-7', 'Empresa 79.964.160-7'),
('78.131.980-5', 'Empresa 78.131.980-5'),
('76.202.903-0', 'Empresa 76.202.903-0'),
('96.719.960-5', 'Empresa 96.719.960-5'),
('78.642.060-1', 'Empresa 78.642.060-1'),
('79.961.920-2', 'Empresa 79.961.920-2'),
('77.903.370-8', 'Empresa 77.903.370-8'),
('87.619.100-8', 'Empresa 87.619.100-8'),
('76.189.347-5', 'Empresa 76.189.347-5'),
('87.627.400-0', 'Empresa 87.627.400-0'),
('77.568.945-5', 'Empresa 77.568.945-5'),
('76.959.850-2', 'Empresa 76.959.850-2'),
('77.684.784-4', 'Empresa 77.684.784-4'),
('76.068.152-0', 'Empresa 76.068.152-0'),
('10.754.961-7', 'Empresa 10.754.961-7'),
('79.554.160-8', 'Empresa 79.554.160-8')
ON CONFLICT (codigo) DO NOTHING;

-- Insertar establecimientos
INSERT INTO establecimientos (nombre, empresa_id) VALUES
('Bahia Rupanco', (SELECT id FROM empresas WHERE codigo = '79.964.160-7')),
('Chiscaihue', (SELECT id FROM empresas WHERE codigo = '79.964.160-7')),
('El Vergel', (SELECT id FROM empresas WHERE codigo = '78.131.980-5')),
('Santa Elena Alto', (SELECT id FROM empresas WHERE codigo = '76.202.903-0')),
('Santa Elena Bajo', (SELECT id FROM empresas WHERE codigo = '76.202.903-0')),
('Eduvigis 2', (SELECT id FROM empresas WHERE codigo = '96.719.960-5')),
('Eduvigis 3', (SELECT id FROM empresas WHERE codigo = '96.719.960-5')),
('Eduvigis 4', (SELECT id FROM empresas WHERE codigo = '96.719.960-5')),
('El Triangulo', (SELECT id FROM empresas WHERE codigo = '96.719.960-5')),
('Los Castaños', (SELECT id FROM empresas WHERE codigo = '78.642.060-1')),
('Quinchilca', (SELECT id FROM empresas WHERE codigo = '79.961.920-2')),
('Tralcan', (SELECT id FROM empresas WHERE codigo = '78.642.060-1')),
('Las Mercedes', (SELECT id FROM empresas WHERE codigo = '79.961.920-2')),
('Purriguin', (SELECT id FROM empresas WHERE codigo = '79.961.920-2')),
('Los Coihues', (SELECT id FROM empresas WHERE codigo = '77.903.370-8')),
('Marafra', (SELECT id FROM empresas WHERE codigo = '87.619.100-8')),
('Las Lomas', (SELECT id FROM empresas WHERE codigo = '76.189.347-5')),
('Arco Iris', (SELECT id FROM empresas WHERE codigo = '87.627.400-0')),
('Rio Futuro', (SELECT id FROM empresas WHERE codigo = '77.568.945-5')),
('San Antonio', (SELECT id FROM empresas WHERE codigo = '76.959.850-2')),
('Los Aromos', (SELECT id FROM empresas WHERE codigo = '77.684.784-4')),
('La Esperanza', (SELECT id FROM empresas WHERE codigo = '76.068.152-0')),
('Volcan', (SELECT id FROM empresas WHERE codigo = '10.754.961-7')),
('Los Maitenes', (SELECT id FROM empresas WHERE codigo = '79.554.160-8'));
