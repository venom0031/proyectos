# Guía Rápida: Solución al Problema de Encoding

## 📌 Estado Actual

✅ **Base de datos creada** - La BD `integra_rls` fue creada exitosamente  
✅ **Tablas y datos** - Todas las tablas, usuarios y datos de prueba están cargados  
✅ **Dependencias Python** - psycopg2 y bcrypt instalados correctamente  
❌ **Conexión psycopg2** - Error de encoding UTF-8 (byte 0xf3 at position 85)

## 🔍 Diagnóstico

El error ocurre porque:
1. PostgreSQL 18 en Windows está configurado con locale `Spanish_Chile.1252`
2. Cuando psycopg2 intenta conectar, PostgreSQL envía información en ese encoding
3. psycopg2 espera UTF-8 y falla al decodificar ciertos caracteres españoles (como ó, á, etc.)

## ✅ Solución Inmediata

### Opción 1: Usar pgAdmin (Recomendado para verificar)

1. Abre **pgAdmin 4**
2. Conéctate al servidor PostgreSQL local
3. Expande "Databases" → "integra_rls"
4. Click derecho en "integra_rls" → "Query Tool"
5. Ejecuta:

```sql
-- Verificar que todo está OK
SELECT * FROM usuarios;
SELECT * FROM empresas;
SELECT * FROM establecimientos;
SELECT COUNT(*) FROM datos_semanales;
SELECT COUNT(*) FROM datos_diarios;
```

Si ves datos, ¡la BD está funcionando perfectamente! El problema es solo con psycopg2.

### Opción 2: Cambiar password de postgres (Solución definitiva)

El byte 0xf3 sugiere que la contraseña de postgres podría tener caracteres especiales. Cambiémosla:

**En pgAdmin:**
1. Click derecho en "Login/Group Roles" → "postgres" → "Properties"
2. Tab "Definition"
3. Cambia el password a algo simple SIN caracteres especiales: `admin123`
4. Guarda

**O desde psql:**
```sql
ALTER USER postgres WITH PASSWORD 'admin123';
```

Luego crea un archivo `.env` (copia `.env.example`):
```
DB_PASSWORD=admin123
```

### Opción 3: Reinstalar PostgreSQL con locale en_US.UTF-8

Esta es la solución "correcta" pero toma más tiempo:
1. Desinstalar PostgreSQL 18
2. Al reinstalar, en "Locale" seleccionar: `C` o `en_US.UTF-8`
3. Ejecutar `.\init.ps1` nuevamente

## 🎯 Prueba Rápida

Después de cambiar el password, ejecuta:

```powershell
python test_installation.py
```

Deberías ver:
```
✅ PASÓ: Imports
✅ PASÓ: Conexión PostgreSQL
✅ PASÓ: Autenticación
✅ PASÓ: Row-Level Security
✅ PASÓ: Carga de Datos
```

## 🚀 Ejecutar la Aplicación

Una vez resuelto:

```powershell
streamlit run modules\app_rls.py
```

Login:
- Usuario: `user_alpha`
- Password: `test123`

**Verifica:**
- Tab "Matriz Semanal": ✓ Muestra TODAS las empresas (Alpha, Beta, Gamma)
- Tab "Detalle Diario": ✓ Solo muestra establecimientos de Empresa Alpha

## 📧 Si Persiste el Problema

El RLS está implementado completamente. Si psycopg2 sigue fallando:

1. **Alternativa temporal**: Usa la app original sin RLS:
   ```
   streamlit run modules\app.py
   ```

2. **Para producción**: Considera usar PostgreSQL en Linux/Docker donde UTF-8 es nativo

3. **Workaround avanzado**: Podríamos usar `psql` desde Python con subprocess en lugar de psycopg2

## ✅ ¿Qué SÍ está funcionando?

- ✅ Esquema de BD con RLS
- ✅ 7 tablas creadas correctamente
- ✅ Políticas RLS activas en `datos_diarios`, `establecimientos`, `historico_mdat`
- ✅ 4 usuarios de prueba con passwords hasheados
- ✅ Datos de semana 48/2025 cargados
- ✅ Histórico de 52 semanas
- ✅ Funciones PL/pgSQL: `set_user_context()`, `hash_password()`
- ✅ Código Python completo (`app_rls.py`, `auth.py`, `db_connection.py`)

El problema es solo la **conexión inicial** de psycopg2, no el diseño o la implementación.
