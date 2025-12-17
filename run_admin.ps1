# PowerShell script para lanzar el admin panel

# Cargar variables desde .env si existe
if (Test-Path .env) {
    Write-Host "Cargando variables desde .env..." -ForegroundColor Yellow
    Get-Content .env | Where-Object { $_ -match '=' -and -not ($_ -match '^#') } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        $value = $value.Trim().Trim('"').Trim("'")
        [System.Environment]::SetEnvironmentVariable($key.Trim(), $value, [System.EnvironmentVariableTarget]::Process)
    }
} else {
    Write-Host "ADVERTENCIA: No se encontró archivo .env. Usando default 'admin'." -ForegroundColor Red
    $env:DB_PASSWORD = "admin"
}

Write-Host "Iniciando Panel de Administración..." -ForegroundColor Green
Write-Host "URL: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

streamlit run admin_panel.py
