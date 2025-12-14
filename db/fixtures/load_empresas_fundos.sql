-- Cargar empresas y establecimientos (fundos) iniciales
-- Basado en datos reales proporcionados

-- Limpiar datos existentes
DELETE FROM datos_diarios;
DELETE FROM datos_semanales;
DELETE FROM historico_mdat;
DELETE FROM establecimientos;
DELETE FROM usuario_empresa;
DELETE FROM usuarios WHERE username != 'admin';
DELETE FROM empresas;

-- Resetear secuencias
ALTER SEQUENCE empresas_id_seq RESTART WITH 1;
ALTER SEQUENCE establecimientos_id_seq RESTART WITH 1;

-- Insertar empresas (sin nombre por ahora, el usuario las editará)
INSERT INTO empresas (codigo, nombre) VALUES 
('79.964.160-7', 'Empresa 79.964.160-7'),
('78.131.980-5', 'Empresa 78.131.980-5'),
('76.202.903-0', 'Empresa 76.202.903-0'),
('96.719.960-5', 'Eduvigis'),
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
('79.554.160-8', 'Empresa 79.554.160-8');

-- Insertar establecimientos (fundos) asociados a cada empresa
-- 79.964.160-7
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '79.964.160-7'), 'Bahia Rupanco'),
((SELECT id FROM empresas WHERE codigo = '79.964.160-7'), 'Chiscaihue');

-- 78.131.980-5
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '78.131.980-5'), 'El Vergel');

-- 76.202.903-0
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '76.202.903-0'), 'Santa Elena Alto'),
((SELECT id FROM empresas WHERE codigo = '76.202.903-0'), 'Santa Elena Bajo');

-- 96.719.960-5 (Eduvigis)
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '96.719.960-5'), 'Eduvigis 2'),
((SELECT id FROM empresas WHERE codigo = '96.719.960-5'), 'Eduvigis 3'),
((SELECT id FROM empresas WHERE codigo = '96.719.960-5'), 'Eduvigis 4'),
((SELECT id FROM empresas WHERE codigo = '96.719.960-5'), 'El Triangulo');

-- 78.642.060-1
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '78.642.060-1'), 'Los Castaños'),
((SELECT id FROM empresas WHERE codigo = '78.642.060-1'), 'Tralcan');

-- 79.961.920-2
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '79.961.920-2'), 'Quinchilca'),
((SELECT id FROM empresas WHERE codigo = '79.961.920-2'), 'Las Mercedes'),
((SELECT id FROM empresas WHERE codigo = '79.961.920-2'), 'Purriguin');

-- 77.903.370-8
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '77.903.370-8'), 'Los Coihues');

-- 87.619.100-8
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '87.619.100-8'), 'Marafra');

-- 76.189.347-5
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '76.189.347-5'), 'Las Lomas');

-- 87.627.400-0
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '87.627.400-0'), 'Arco Iris');

-- 77.568.945-5
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '77.568.945-5'), 'Rio Futuro');

-- 76.959.850-2
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '76.959.850-2'), 'San Antonio');

-- 77.684.784-4
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '77.684.784-4'), 'Los Aromos');

-- 76.068.152-0
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '76.068.152-0'), 'La Esperanza');

-- 10.754.961-7
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '10.754.961-7'), 'Volcan');

-- 79.554.160-8
INSERT INTO establecimientos (empresa_id, nombre) VALUES 
((SELECT id FROM empresas WHERE codigo = '79.554.160-8'), 'Los Maitenes');

-- Resumen
SELECT 'Datos cargados exitosamente' as status;
SELECT COUNT(*) as total_empresas FROM empresas;
SELECT COUNT(*) as total_establecimientos FROM establecimientos;

-- Mostrar resumen de carga
SELECT e.codigo, e.nombre as empresa, COUNT(est.id) as fundos
FROM empresas e
LEFT JOIN establecimientos est ON e.id = est.empresa_id
GROUP BY e.codigo, e.nombre
ORDER BY e.codigo;
