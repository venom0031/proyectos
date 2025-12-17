# Script final para ejecutar la app

Write-Host "===============================================" -ForegroundColor Green
Write-Host "Ejecutando Streamlit con RLS" -ForegroundColor Green  
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""

# Cargar variables desde .env si existe
if (Test-Path .env) {
    Write-Host "Cargando variables desde .env..." -ForegroundColor Yellow
    Get-Content .env | Where-Object { $_ -match '=' -and -not ($_ -match '^#') } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        # Remover comillas si existen
        $value = $value.Trim().Trim('"').Trim("'")
        $env_key = $key.Trim()
        
        # Setear variable de entorno
        [System.Environment]::SetEnvironmentVariable($env_key, $value, [System.EnvironmentVariableTarget]::Process)
    }
} else {
    Write-Host "ADVERTENCIA: No se encontró archivo .env. Usando defaults inseguros." -ForegroundColor Red
    $env:DB_PASSWORD = "admin"
}

Write-Host "DB User: $env:DB_USER" -ForegroundColor Gray
Write-Host "DB Name: $env:DB_NAME" -ForegroundColor Gray
Write-Host ""

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
