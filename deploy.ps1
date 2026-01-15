#!/usr/bin/env pwsh
# ==============================================================================
# INTEGRA - Reporteria Deployment Script
# ==============================================================================
# Proyecto: Sistema de Reportería con PostgreSQL y Redis
# Puerto: 8502 (Admin: 8503)
# ==============================================================================

$ErrorActionPreference = "Stop"

# Configuración
$CLIENT_NAME = "integra"
$PROJECT_NAME = "reporteria"
$SERVER_USER = "debian"
$SERVER_IP = "51.222.87.227"
$REMOTE_DIR = "/home/debian/clientes/$CLIENT_NAME/$PROJECT_NAME"

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       DESPLIEGUE - INTEGRA REPORTERIA                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ Error: Ejecuta este script desde c:\new\clientes\INTEGRA\Reporteria\" -ForegroundColor Red
    exit 1
}

# Crear directorio temporal para deploy
$TEMP_DIR = "deploy_temp"
if (Test-Path $TEMP_DIR) { Remove-Item -Recurse -Force $TEMP_DIR }
New-Item -ItemType Directory -Force -Path $TEMP_DIR | Out-Null

Write-Host "📦 Copiando archivos del proyecto..." -ForegroundColor Yellow

# Copiar estructura
Copy-Item -Path "modules" -Destination "$TEMP_DIR\modules" -Recurse -Force
Copy-Item -Path "db" -Destination "$TEMP_DIR\db" -Recurse -Force
Copy-Item -Path "data" -Destination "$TEMP_DIR\data" -Recurse -Force
Copy-Item -Path "scripts" -Destination "$TEMP_DIR\scripts" -Recurse -Force
Copy-Item -Path "backups" -Destination "$TEMP_DIR\backups" -Recurse -Force

# Copiar archivos raíz
Copy-Item -Path "admin_panel.py" -Destination "$TEMP_DIR\" -Force
Copy-Item -Path "requirements.txt" -Destination "$TEMP_DIR\" -Force
Copy-Item -Path "README.md" -Destination "$TEMP_DIR\" -Force

# Copiar templates de configuración (NO los .env originales)
if (Test-Path ".env.template") {
    Copy-Item -Path ".env.template" -Destination "$TEMP_DIR\" -Force
}

# Limpiar __pycache__
Write-Host "🧹 Limpiando archivos temporales..." -ForegroundColor Yellow
Get-ChildItem -Path $TEMP_DIR -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $TEMP_DIR -Recurse -Filter "*.pyc" | Remove-Item -Force

# Crear archivo .rsyncignore
@"
__pycache__/
*.pyc
*.pyo
*.log
.git/
.vscode/
.env
.env.local
*.db
logs/
_obsolete/
deploy_temp/
"@ | Out-File -FilePath "$TEMP_DIR\.rsyncignore" -Encoding utf8

Write-Host "📤 Subiendo al servidor..." -ForegroundColor Yellow

# Crear estructura en servidor
ssh "${SERVER_USER}@${SERVER_IP}" "mkdir -p $REMOTE_DIR"

# Sincronizar archivos usando rsync
Write-Host "🔄 Sincronizando con rsync..." -ForegroundColor Yellow
rsync -avz --delete `
    --exclude='__pycache__' `
    --exclude='*.pyc' `
    --exclude='.git' `
    --exclude='.env' `
    --exclude='logs/' `
    --exclude='_obsolete/' `
    "$TEMP_DIR/" "${SERVER_USER}@${SERVER_IP}:$REMOTE_DIR/"

# Limpiar directorio temporal
Remove-Item -Recurse -Force $TEMP_DIR

Write-Host "`n✅ Archivos subidos correctamente" -ForegroundColor Green
Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║                  PASOS POST-DEPLOY                             ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Yellow

Write-Host "1️⃣  Conectar al servidor:" -ForegroundColor Cyan
Write-Host "   ssh ${SERVER_USER}@${SERVER_IP}`n" -ForegroundColor White

Write-Host "2️⃣  Configurar variables de entorno:" -ForegroundColor Cyan
Write-Host "   cd $REMOTE_DIR" -ForegroundColor White
Write-Host "   cp .env.template .env" -ForegroundColor White
Write-Host "   nano .env  # Editar con credenciales reales`n" -ForegroundColor White

Write-Host "3️⃣  Instalar dependencias:" -ForegroundColor Cyan
Write-Host "   pip install -r requirements.txt`n" -ForegroundColor White

Write-Host "4️⃣  Inicializar PostgreSQL:" -ForegroundColor Cyan
Write-Host "   cd db/schema" -ForegroundColor White
Write-Host "   psql -U postgres -d integra_rls -f init_db.sql`n" -ForegroundColor White

Write-Host "5️⃣  Iniciar servicios:" -ForegroundColor Cyan
Write-Host "   sudo systemctl enable integra-reporteria" -ForegroundColor White
Write-Host "   sudo systemctl start integra-reporteria" -ForegroundColor White
Write-Host "   sudo systemctl status integra-reporteria`n" -ForegroundColor White

Write-Host "6️⃣  Acceder al dashboard:" -ForegroundColor Cyan
Write-Host "   http://51.222.87.227:8502 (App principal)" -ForegroundColor White
Write-Host "   http://51.222.87.227:8503 (Panel Admin)`n" -ForegroundColor White

Write-Host "📝 Nota: Necesitas PostgreSQL 16+ y Redis instalados" -ForegroundColor Yellow
Write-Host "📚 Ver README.md para más detalles`n" -ForegroundColor Yellow
