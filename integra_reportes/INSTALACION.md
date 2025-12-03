# Guía de Instalación Paso a Paso

## Problema 1: psql no encontrado ❌

**Síntoma:**
```
psql : El término 'psql' no se reconoce como nombre de un cmdlet...
```

**Solución:**

### Opción A: Encontrar PostgreSQL y ejecutar directamente

1. Ejecuta el script de búsqueda:
```powershell
.\find_postgres.ps1
```

2. El script te mostrará la ruta de `psql.exe` y cómo usarlo

3. Ejecuta usando la ruta completa, ejemplo:
```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -f db\init_db.sql
```

### Opción B: Agregar PostgreSQL al PATH

1. Busca la carpeta `bin` de PostgreSQL (normalmente en `C:\Program Files\PostgreSQL\[versión]\bin`)

2. Temporalmente (solo esta sesión de PowerShell):
```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
psql -U postgres -f db\init_db.sql
```

3. Permanentemente:
   - Abre "Variables de entorno" desde el Panel de Control
   - Edita la variable `Path` del sistema
   - Agrega la ruta de PostgreSQL `bin`
   - Reinicia PowerShell

### Opción C: Usar pgAdmin (GUI)

1. Abre pgAdm in 4
2. Conecta a tu servidor PostgreSQL local
3. Click derecho en "Databases" → "Query Tool"
4. Abre y ejecuta `db\init_db.sql`

## Problema 2: Error de encoding UTF-8 ❌

**Síntoma:**
```
'utf-8' codec can't decode byte 0xf3 in position 85: invalid continuation byte
```

**Solución:** ✅ Ya corregido

He actualizado:
- `db\init_db.sql` - Cambiado a encoding UTF8 con LC_COLLATE='C'
- `modules\db_connection.py` - Agregado `client_encoding='utf8'`

## Verificación de Instalación

Una vez que PostgreSQL esté en el PATH:

```powershell
# 1. Verificar que psql funciona
psql --version

# 2. Inicializar la base de datos
psql -U postgres -f db\init_db.sql
# Ingresa la contraseña de postgres cuando se solicite

# 3. Verificar instalación
python test_installation.py

# 4. Ejecutar la aplicación
streamlit run modules\app_rls.py
```

## Resultado Esperado

```
============================================================
PRUEBA DE INSTALACIÓN - PostgreSQL RLS
============================================================

🔧 Probando imports...
  ✓ psycopg2
  ✓ bcrypt
  ✓ config
  ✓ db_connection
  ✓ auth
✅ Todos los módulos importados correctamente

🔌 Probando conexión a PostgreSQL...
  Host: localhost
  Puerto: 5432
  Base de datos: integra_rls
  Usuario: postgres
✅ Conexión exitosa

🔐 Probando autenticación...
  ✓ user_alpha: autenticado correctamente
  ✓ user_beta: autenticado correctamente
  ✓ admin: autenticado correctamente
✅ Autenticación funcionando correctamente

🛡️  Probando Row-Level Security...
  Test 1: user_alpha (ID=1) debe ver solo Empresa Alpha
    ✓ Solo ve: Empresa Alpha
  Test 2: admin debe ver todas las empresas
    ✓ Ve 3 empresas: Empresa Alpha, Empresa Beta, Empresa Gamma
✅ RLS funcionando correctamente

📊 Probando carga de datos...
  Cargando datos semanales...
    ✓ XX registros cargados
    ✓ X establecimientos
    ✓ 3 empresas (debe ser 3 para ranking público)
✅ Datos semanales cargados correctamente (todas las empresas)

============================================================
RESUMEN DE PRUEBAS
============================================================
✅ PASÓ: Imports
✅ PASÓ: Conexión PostgreSQL
✅ PASÓ: Autenticación
✅ PASÓ: Row-Level Security
✅ PASÓ: Carga de Datos

🎉 ¡Todas las pruebas pasaron! La instalación está completa.
```

## Troubleshooting Adicional

### PostgreSQL no está corriendo

```powershell
# Verificar servicio
Get-Service -Name postgresql*

# Iniciar servicio (requiere admin)
Start-Service postgresql-x64-16  # Ajustar nombre según versión
```

### No sabes la contraseña de postgres

Durante la instalación de PostgreSQL, configuraste una contraseña. Si la olvidaste:

1. Busca el archivo `pg_hba.conf` (en `C:\Program Files\PostgreSQL\[versión]\data\`)
2. Cambia `md5` por `trust` temporalmente
3. Reinicia el servicio PostgreSQL
4. Conecta sin contraseña y cámbiala:
   ```sql
   ALTER USER postgres WITH PASSWORD 'nueva_contraseña';
   ```
5. Revertir `pg_hba.conf` a `md5`
6. Reiniciar servicio

### Puerto 5432 ocupado

Si otro servicio usa el puerto 5432, modifica `.env`:

```
DB_PORT=5433  # o el puerto que uses
```

## Usuarios de Prueba

Una vez que todo funcione:

| Usuario | Contraseña | Acceso |
|---------|------------|--------|
| `user_alpha` | `test123` | Solo Empresa Alpha |
| `user_beta` | `test123` | Solo Empresa Beta |
| `user_multi` | `test123` | Empresas Alpha y Gamma |
| `admin` | `admin123` | Todas las empresas |
