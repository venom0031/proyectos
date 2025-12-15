# Guía de Respaldo y Restauración de Base de Datos

Este documento detalla el procedimiento para realizar respaldos y restauraciones de la base de datos `integra_rls`.

## Requisitos Previos

- PostgreSQL instalado (versión 17 o superior recomendada).
- Acceso a la línea de comandos (PowerShell o Bash).
- Credenciales de la base de datos (ver archivo `.env`).

## Respaldo (Backup)

Para generar un respaldo completo de la base de datos, ejecuta el siguiente comando en PowerShell. Asegúrate de ajustar la ruta a `pg_dump.exe` si es necesario.

### Comando

```powershell
$env:PGPASSWORD="admin"; & "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -F p -f "integra_rls_backup.sql" integra_rls
```

> **Nota:** Si encuentras un error de versión ("server version: 18.0; pg_dump version: 17.7"), intenta usar el ejecutable de la versión 18:
> `"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"`

### Detalles del Archivo Generado

- **Nombre:** `integra_rls_backup.sql`
- **Formato:** SQL plano (Plain text)
- **Ubicación:** Directorio raíz del proyecto (por defecto)

## Restauración (Restore)

Para restaurar la base de datos en un nuevo servidor o entorno local:

1. **Crear la base de datos (si no existe):**
   ```bash
   createdb -h localhost -p 5432 -U postgres integra_rls
   ```

2. **Importar el respaldo:**
   ```bash
   psql -h localhost -p 5432 -U postgres -d integra_rls -f integra_rls_backup.sql
   ```

## Solución de Problemas Comunes

- **Error de autenticación:** Verifica que la contraseña en `.env` o en `$env:PGPASSWORD` sea correcta.
- **Error de versión de `pg_dump`:** Asegúrate de que `pg_dump` sea de una versión igual o mayor a la del servidor PostgreSQL.
- **Conexión rechazada:** Verifica que el servicio de PostgreSQL esté corriendo y escuchando en el puerto configurado (5432).
