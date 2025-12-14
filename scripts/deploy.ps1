# PowerShell script for quick Docker deployment on Windows
# Usage: .\scripts\deploy.ps1

param(
    [string]$Environment = "production"
)

Write-Host "🚀 Iniciando despliegue Integra - Ambiente: $Environment" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green

# 1. Verificar requisitos
Write-Host "✓ Verificando requisitos..." -ForegroundColor Cyan

try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker no está instalado o no está en PATH" -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Docker Compose no está instalado o no está en PATH" -ForegroundColor Red
    exit 1
}

# 2. Verificar .env
Write-Host "✓ Verificando configuración..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$envFile = Join-Path $projectRoot ".env"
$envExampleFile = Join-Path $projectRoot ".env.example"

if (-not (Test-Path $envFile)) {
    Write-Host "⚠️  Archivo .env no encontrado. Copiando desde .env.example..." -ForegroundColor Yellow
    Copy-Item $envExampleFile $envFile
    Write-Host "⚠️  IMPORTANTE: Edita $envFile con valores reales" -ForegroundColor Yellow
    Read-Host "Presiona Enter después de editar .env"
}

# 3. Crear directorios necesarios
Write-Host "✓ Creando directorios..." -ForegroundColor Cyan
$logsDir = Join-Path $projectRoot "logs"
$dataDir = Join-Path $projectRoot "data"

if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }

# 4. Build y start
Write-Host "✓ Construyendo imágenes Docker..." -ForegroundColor Cyan
Push-Location $projectRoot
docker-compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error construyendo imágenes Docker" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Iniciando servicios..." -ForegroundColor Cyan
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error iniciando servicios" -ForegroundColor Red
    exit 1
}

# 5. Esperar a que PostgreSQL esté listo
Write-Host "✓ Esperando a que PostgreSQL esté listo..." -ForegroundColor Cyan
$attempts = 0
$maxAttempts = 30

while ($attempts -lt $maxAttempts) {
    try {
        $output = docker-compose exec -T db psql -U postgres -c "SELECT 1" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ PostgreSQL está listo" -ForegroundColor Green
            break
        }
    } catch {}
    
    $attempts++
    Write-Host "  Intento $attempts/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($attempts -eq $maxAttempts) {
    Write-Host "⚠️  PostgreSQL no respondió después de 60 segundos. Verificar logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs db" -ForegroundColor Gray
}

# 6. Verificar estado
Write-Host ""
Write-Host "✓ Verificando estado de servicios..." -ForegroundColor Cyan
docker-compose ps

Pop-Location

# Resumen
Write-Host ""
Write-Host "✅ Despliegue completado exitosamente" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Acceso:" -ForegroundColor Cyan
Write-Host "  App principal: http://localhost:8501" -ForegroundColor White
Write-Host "  Admin panel:   http://localhost:8502" -ForegroundColor White
Write-Host ""
Write-Host "Comandos útiles:" -ForegroundColor Cyan
Write-Host "  Ver logs en vivo:" -ForegroundColor Gray
Write-Host "    docker-compose logs -f app" -ForegroundColor White
Write-Host "  Detener servicios:" -ForegroundColor Gray
Write-Host "    docker-compose down" -ForegroundColor White
Write-Host "  Reiniciar servicios:" -ForegroundColor Gray
Write-Host "    docker-compose restart" -ForegroundColor White
Write-Host ""
