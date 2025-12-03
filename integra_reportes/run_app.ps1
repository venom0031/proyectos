# # Script final para ejecutar la app

Write-Host "===============================================" -ForegroundColor Green
Write-Host "Ejecutando Streamlit con RLS" -ForegroundColor Green  
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Password BD: admin" -ForegroundColor Cyan
Write-Host ""

# Setear variables de entorno
$env:DB_PASSWORD = "admin"

# Matar streamlit prev si existe
$streamlit_procs = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
if ($streamlit_procs) {
    Write-Host "Deteniendo instancias previas de Streamlit..." -ForegroundColor Yellow
    $streamlit_procs | Stop-Process -Force
    Start-Sleep -Seconds 2
}

Write-Host "Iniciando app..." -ForegroundColor Cyan
Write-Host ""

streamlit run modules\app_rls.py
