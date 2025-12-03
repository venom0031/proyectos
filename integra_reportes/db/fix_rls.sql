-- Arreglar RLS: datos_semanales SIN RLS (público)
-- datos_diarios, establecimientos, historico_mdat CON RLS

-- DESACTIVAR RLS en datos_semanales (ranking público)
ALTER TABLE datos_semanales DISABLE ROW LEVEL SECURITY;

-- CONFIRMAR RLS activo en otras tablas
ALTER TABLE datos_diarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE establecimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_mdat ENABLE ROW LEVEL SECURITY;

-- Verificar políticas
\d datos_semanales
\d datos_diarios
\d establecimientos
\d historico_mdat

SELECT 'RLS Configuration Updated!' as status;
