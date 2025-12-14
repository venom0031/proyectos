# Script para encontrar la instalacion de PostgreSQL en Windows

Write-Host "============================================" -ForegroundColor Green
Write-Host "Buscando PostgreSQL en el sistema..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Buscar en ubicaciones comunes
$commonPaths = @(
    "C:\Program Files\PostgreSQL\*\bin",
    "C:\Program Files (x86)\PostgreSQL\*\bin",
    "C:\PostgreSQL\*\bin"
)

$found = $false
$foundPath = ""

foreach ($pathPattern in $commonPaths) {
    $paths = Get-Item $pathPattern -ErrorAction SilentlyContinue
    
    if ($paths) {
        foreach ($path in $paths) {
            $psqlPath = Join-Path $path.FullName "psql.exe"
            if (Test-Path $psqlPath) {
                Write-Host "Encontrado PostgreSQL:" -ForegroundColor Green
                Write-Host "  Ruta: $($path.FullName)" -ForegroundColor White
                Write-Host ""
                
                # Verificar version
                try {
                    $version = & $psqlPath --version 2>&1
                    Write-Host "  Version: $version" -ForegroundColor Cyan
                } catch {
                    Write-Host "  No se pudo obtener version" -ForegroundColor Yellow
                }
                
                Write-Host ""
                $found = $true
                $foundPath = $path.FullName
                break
            }
        }
        if ($found) { break }
    }
}

if (-not $found) {
    Write-Host "PostgreSQL NO encontrado en ubicaciones comunes" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles soluciones:" -ForegroundColor Yellow
    Write-Host "  1. Verifica que PostgreSQL este instalado" -ForegroundColor White
    Write-Host "  2. Usa pgAdmin para ejecutar db\init_db.sql" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "Para ejecutar la inicializacion, copia y pega:" -ForegroundColor Yellow
    Write-Host ""
    $commandToRun = "`$env:Path += `";$foundPath`"; psql -U postgres -f db\init_db.sql"
    Write-Host $commandToRun -ForegroundColor Green
    Write-Host ""
}

Write-Host ""
pause
