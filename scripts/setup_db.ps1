# Script de ayuda para inicializar la base de datos
# Ejecutar desde PowerShell en Windows

Write-Host "============================================" -ForegroundColor Green
Write-Host "Inicialización de Base de Datos integra_rls" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Verificar que psql está disponible
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue

if (-not $psqlPath) {
    Write-Host "ERROR: psql no encontrado en PATH" -ForegroundColor Red
    Write-Host "Asegúrate de tener PostgreSQL instalado y agregado al PATH" -ForegroundColor Yellow
    Write-Host "Ejemplo de ruta: C:\Program Files\PostgreSQL\15\bin" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ psql encontrado: $($psqlPath.Source)" -ForegroundColor Green
Write-Host ""

# Solicitar credenciales
Write-Host "Ingrese credenciales de PostgreSQL:" -ForegroundColor Cyan
$pgUser = Read-Host "Usuario PostgreSQL (default: postgres)"
if ([string]::IsNullOrWhiteSpace($pgUser)) {
    $pgUser = "postgres"
}

Write-Host ""
Write-Host "NOTA: La contraseña se solicitará en la ventana de psql" -ForegroundColor Yellow
Write-Host ""

# Navegar al directorio db
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dbDir = Join-Path $scriptDir "db"

if (-not (Test-Path $dbDir)) {
    Write-Host "ERROR: Directorio db/ no encontrado" -ForegroundColor Red
    Write-Host "Ruta esperada: $dbDir" -ForegroundColor Yellow
    pause
    exit 1
}

Set-Location $dbDir

Write-Host "Ejecutando init_db.sql..." -ForegroundColor Cyan
Write-Host ""

# Ejecutar script
$initScript = Join-Path $dbDir "init_db.sql"

if (-not (Test-Path $initScript)) {
    Write-Host "ERROR: init_db.sql no encontrado" -ForegroundColor Red
    pause
    exit 1
}

& psql -U $pgUser -f $initScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "✓ Base de datos inicializada exitosamente" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usuarios de prueba creados:" -ForegroundColor Cyan
    Write-Host "  - user_alpha (password: test123) -> Solo Empresa Alpha" -ForegroundColor White
    Write-Host "  - user_beta (password: test123) -> Solo Empresa Beta" -ForegroundColor White
    Write-Host "  - user_multi (password: test123) -> Empresa Alpha y Gamma" -ForegroundColor White
    Write-Host "  - admin (password: admin123) -> Todas las empresas" -ForegroundColor White
    Write-Host ""
    Write-Host "Siguiente paso:" -ForegroundColor Cyan
    Write-Host "  streamlit run modules\app_rls.py" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Hubo un problema al inicializar la base de datos" -ForegroundColor Red
    Write-Host "Revisa los mensajes de error arriba" -ForegroundColor Yellow
    Write-Host ""
}

# Volver al directorio original
Set-Location $scriptDir

pause
