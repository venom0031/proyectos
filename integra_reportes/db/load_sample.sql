-- Script SQL para cargar datos de muestra directamente

-- Limpiar
DELETE FROM datos_diarios;
DELETE FROM datos_semanales;
DELETE FROM historico_mdat;
DELETE FROM establecimientos;
DELETE FROM usuario_empresa;
DELETE FROM usuarios;
DELETE FROM empresas;

-- Resetear secuencias
ALTER SEQUENCE empresas_id_seq RESTART WITH 1;
ALTER SEQUENCE usuarios_id_seq RESTART WITH 1;
ALTER SEQUENCE establecimientos_id_seq RESTART WITH 1;
ALTER SEQUENCE datos_semanales_id_seq RESTART WITH 1;

-- Admin
INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo)
VALUES ('admin', hash_password('admin123'), 'Administrador', 'admin@integra.cl', true, true);

-- Empresas
INSERT INTO empresas (codigo, nombre) VALUES ('96.719.960-5', 'Eduvigis');
INSERT INTO empresas (codigo, nombre) VALUES ('79.964.160-7', 'Los Lagos');

-- Establecimientos
INSERT INTO establecimientos (empresa_id, nombre) VALUES (1, 'Eduvigis 2');
INSERT INTO establecimientos (empresa_id, nombre) VALUES (1, 'Eduvigis 3');
INSERT INTO establecimientos (empresa_id, nombre) VALUES (2, 'Bahia Rupanco');
INSERT INTO establecimientos (empresa_id, nombre) VALUES (2, 'Chiscaihue');

-- Datos semanales (valores de ejemplo)
INSERT INTO datos_semanales (establecimiento_id, empresa_id, semana, anio, vacas_masa, vacas_en_ordena, produccion_promedio, mdat)
VALUES 
(1, 1, 40, 2024, 650, 520, 28.5, 9500),
(2, 1, 40, 2024, 720, 600, 31.2, 11200),
(3, 2, 40, 2024, 580, 480, 26.8, 8800),
(4, 2, 40, 2024, 690, 550, 29.5, 10300);

-- Usuarios
INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo)
VALUES ('user_eduvigis', hash_password('test123'), 'Usuario Eduvigis', 'eduvigis@integra.cl', false, true);

INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo)
VALUES ('user_lagos', hash_password('test123'), 'Usuario Los Lagos', 'lagos@integra.cl', false, true);

-- Asociaciones usuario-empresa
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES (2, 1); -- user_eduvigis -> Eduvigis
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES (3, 2); -- user_lagos -> Los Lagos
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES (1, 1); -- admin -> ambas
INSERT INTO usuario_empresa (usuario_id, empresa_id) VALUES (1, 2);

-- Verificar
SELECT 'Datos cargados correctamente' as resultado;
SELECT COUNT(*) as empresas FROM empresas;
SELECT COUNT(*) as establecimientos FROM establecimientos;
SELECT COUNT(*) as usuarios FROM usuarios;
SELECT COUNT(*) as datos_semanales FROM datos_semanales;
