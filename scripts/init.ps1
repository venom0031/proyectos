# ============================================
# Script Simplificado de Inicialización
# ============================================

Write-Host ""
Write-Host "Inicializando base de datos integra_rls..." -ForegroundColor Cyan
Write-Host ""

# Ruta correcta para PostgreSQL 18
$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# Verificar que existe
if (-not (Test-Path $psqlPath)) {
    Write-Host "ERROR: PostgreSQL no encontrado en $psqlPath" -ForegroundColor Red
    pause
    exit 1
}

# Ejecutar script de inicialización
Write-Host "Ejecutando init_db.sql..." -ForegroundColor Yellow
Write-Host "Se te pedirá la contraseña del usuario 'postgres'" -ForegroundColor Yellow
Write-Host ""

& $psqlPath -U postgres -f "db\init_db.sql"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "Base de datos inicializada correctamente!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Siguiente paso:" -ForegroundColor Cyan
    Write-Host "  python test_installation.py" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Hubo un problema al inicializar" -ForegroundColor Red
    Write-Host ""
}

pause
