#!/bin/bash
# ==============================================================================
# Server Setup Script - INTEGRA Reporteria
# ==============================================================================
# Este script configura el servidor para el proyecto Reporteria
# Requisitos: PostgreSQL 16+, Redis, Python 3.13+
# ==============================================================================

set -e

CLIENT_NAME="integra"
PROJECT_NAME="reporteria"
APP_PORT=8502
ADMIN_PORT=8503
BASE_DIR="/home/debian/clientes/$CLIENT_NAME/$PROJECT_NAME"
VENV_DIR="$BASE_DIR/venv"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      CONFIGURACIÓN SERVIDOR - INTEGRA REPORTERIA                ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Verificar que el directorio existe
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ Error: $BASE_DIR no existe. Ejecuta deploy.ps1 primero"
    exit 1
fi

cd "$BASE_DIR"

# ==============================================================================
# 1. CREAR ENTORNO VIRTUAL
# ==============================================================================
echo ""
echo "1️⃣  Creando entorno virtual Python..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "✅ Entorno virtual creado"

# ==============================================================================
# 2. INSTALAR DEPENDENCIAS
# ==============================================================================
echo ""
echo "2️⃣  Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencias instaladas"

# ==============================================================================
# 3. VERIFICAR POSTGRESQL
# ==============================================================================
echo ""
echo "3️⃣  Verificando PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL no está instalado"
    echo "   Instalar con: sudo apt install postgresql-16 postgresql-contrib-16"
else
    PG_VERSION=$(psql --version | grep -oP '\d+\.\d+' | head -1)
    echo "✅ PostgreSQL $PG_VERSION instalado"
fi

# ==============================================================================
# 4. VERIFICAR REDIS
# ==============================================================================
echo ""
echo "4️⃣  Verificando Redis..."
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis no está instalado"
    echo "   Instalar con: sudo apt install redis-server"
else
    REDIS_VERSION=$(redis-cli --version | grep -oP '\d+\.\d+\.\d+')
    echo "✅ Redis $REDIS_VERSION instalado"
fi

# ==============================================================================
# 5. CREAR SERVICIO SYSTEMD - APP PRINCIPAL
# ==============================================================================
echo ""
echo "5️⃣  Creando servicio systemd (App Principal - Puerto $APP_PORT)..."

sudo tee /etc/systemd/system/integra-reporteria.service > /dev/null <<EOF
[Unit]
Description=INTEGRA Reporteria - App Principal
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=debian
WorkingDirectory=$BASE_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/streamlit run modules/app.py \\
    --server.port=$APP_PORT \\
    --server.address=0.0.0.0 \\
    --server.headless=true \\
    --browser.gatherUsageStats=false

Restart=always
RestartSec=10
StandardOutput=append:/var/log/integra-reporteria.log
StandardError=append:/var/log/integra-reporteria-error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Servicio App Principal creado"

# ==============================================================================
# 6. CREAR SERVICIO SYSTEMD - ADMIN PANEL
# ==============================================================================
echo ""
echo "6️⃣  Creando servicio systemd (Admin Panel - Puerto $ADMIN_PORT)..."

sudo tee /etc/systemd/system/integra-reporteria-admin.service > /dev/null <<EOF
[Unit]
Description=INTEGRA Reporteria - Panel Admin
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=debian
WorkingDirectory=$BASE_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/streamlit run admin_panel.py \\
    --server.port=$ADMIN_PORT \\
    --server.address=0.0.0.0 \\
    --server.headless=true \\
    --browser.gatherUsageStats=false

Restart=always
RestartSec=10
StandardOutput=append:/var/log/integra-reporteria-admin.log
StandardError=append:/var/log/integra-reporteria-admin-error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Servicio Admin Panel creado"

# ==============================================================================
# 7. CONFIGURAR NGINX (Si está instalado)
# ==============================================================================
echo ""
echo "7️⃣  Configurando Nginx..."

if command -v nginx &> /dev/null; then
    sudo tee /etc/nginx/sites-available/integra-reporteria > /dev/null <<'NGINX_EOF'
# INTEGRA Reporteria - App Principal
server {
    listen 80;
    server_name reporteria.integra.local;

    location / {
        proxy_pass http://localhost:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}

# INTEGRA Reporteria - Admin Panel
server {
    listen 80;
    server_name admin.reporteria.integra.local;

    location / {
        proxy_pass http://localhost:8503;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
NGINX_EOF

    # Habilitar sitio
    sudo ln -sf /etc/nginx/sites-available/integra-reporteria /etc/nginx/sites-enabled/
    
    # Test y reload
    sudo nginx -t && sudo systemctl reload nginx
    
    echo "✅ Nginx configurado"
else
    echo "⚠️  Nginx no instalado - Saltando configuración"
fi

# ==============================================================================
# 8. CONFIGURAR FIREWALL
# ==============================================================================
echo ""
echo "8️⃣  Configurando firewall (UFW)..."

if command -v ufw &> /dev/null; then
    sudo ufw allow $APP_PORT/tcp comment "INTEGRA Reporteria App"
    sudo ufw allow $ADMIN_PORT/tcp comment "INTEGRA Reporteria Admin"
    echo "✅ Firewall configurado"
else
    echo "⚠️  UFW no instalado"
fi

# ==============================================================================
# 9. RECARGAR SYSTEMD
# ==============================================================================
echo ""
echo "9️⃣  Recargando systemd..."
sudo systemctl daemon-reload

echo "✅ Systemd recargado"

# ==============================================================================
# 10. CREAR DIRECTORIOS DE LOGS
# ==============================================================================
echo ""
echo "🔟 Creando directorios de logs..."
sudo touch /var/log/integra-reporteria.log
sudo touch /var/log/integra-reporteria-error.log
sudo touch /var/log/integra-reporteria-admin.log
sudo touch /var/log/integra-reporteria-admin-error.log
sudo chown debian:debian /var/log/integra-reporteria*.log

mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/backups"

echo "✅ Directorios creados"

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ CONFIGURACIÓN COMPLETADA                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 PASOS SIGUIENTES:"
echo ""
echo "1️⃣  Configurar variables de entorno:"
echo "   cd $BASE_DIR"
echo "   cp .env.template .env"
echo "   nano .env  # Editar con credenciales"
echo ""
echo "2️⃣  Crear base de datos PostgreSQL:"
echo "   sudo -u postgres createdb integra_rls"
echo "   sudo -u postgres psql -d integra_rls -f db/schema/init_db.sql"
echo ""
echo "3️⃣  Iniciar servicios:"
echo "   sudo systemctl enable integra-reporteria"
echo "   sudo systemctl enable integra-reporteria-admin"
echo "   sudo systemctl start integra-reporteria"
echo "   sudo systemctl start integra-reporteria-admin"
echo ""
echo "4️⃣  Verificar estado:"
echo "   sudo systemctl status integra-reporteria"
echo "   sudo systemctl status integra-reporteria-admin"
echo ""
echo "5️⃣  Ver logs:"
echo "   sudo journalctl -u integra-reporteria -f"
echo "   sudo journalctl -u integra-reporteria-admin -f"
echo ""
echo "🌐 ACCESO:"
echo "   App Principal: http://51.222.87.227:$APP_PORT"
echo "   Panel Admin:   http://51.222.87.227:$ADMIN_PORT"
echo ""
echo "📚 Documentación completa en README.md"
echo ""
