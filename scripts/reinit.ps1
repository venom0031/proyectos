# Script simplificado para reinicializar con password correcta

Write-Host ""
Write-Host "Reinicializando base de datos integra_rls..." -ForegroundColor Cyan
Write-Host "Password: admin" -ForegroundColor Yellow
Write-Host ""

$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

& $psqlPath -U postgres -f "db\init_db_windows.sql"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "Base de datos lista!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Probando conexion:" -ForegroundColor Cyan
    Write-Host "  `$env:DB_PASSWORD=`"admin`"; python test_installation.py" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR al inicializar" -ForegroundColor Red
    Write-Host ""
}

pause
