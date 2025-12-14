# PowerShell script para lanzar el admin panel
$env:DB_PASSWORD = "admin"

Write-Host "Iniciando Panel de Administración..." -ForegroundColor Green
Write-Host "URL: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

streamlit run admin_panel.py
