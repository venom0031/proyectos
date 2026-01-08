#!/bin/bash
# =====================================================
# Script de Instalación Rápida para Debian 13
# Ejecutar como root: bash setup-vps.sh
# =====================================================

set -e  # Salir si hay error

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════╗"
echo "║     INTEGRA SpA - Instalación VPS                  ║"
echo "║     Debian 13 (Trixie)                             ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =====================================================
# PASO 1: Verificar que somos root
# =====================================================
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script debe ejecutarse como root${NC}"
    echo "   Usa: sudo bash setup-vps.sh"
    exit 1
fi

# =====================================================
# PASO 2: Actualizar sistema
# =====================================================
echo -e "\n${YELLOW}📦 Paso 1/6: Actualizando sistema...${NC}"
apt update && apt upgrade -y

# =====================================================
# PASO 3: Instalar dependencias
# =====================================================
echo -e "\n${YELLOW}📦 Paso 2/6: Instalando dependencias...${NC}"
apt install -y \
    curl \
    git \
    wget \
    nano \
    htop \
    ufw \
    fail2ban \
    openssl \
    ca-certificates \
    gnupg \
    lsb-release \
    rsync

# =====================================================
# PASO 4: Instalar Docker
# =====================================================
echo -e "\n${YELLOW}🐳 Paso 3/6: Instalando Docker...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker ya está instalado${NC}"
else
    # Agregar repositorio de Docker
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    systemctl enable docker
    systemctl start docker
    
    echo -e "${GREEN}✓ Docker instalado correctamente${NC}"
fi

docker --version
docker compose version

# =====================================================
# PASO 5: Crear usuario integra
# =====================================================
echo -e "\n${YELLOW}👤 Paso 4/6: Configurando usuario...${NC}"

if id "integra" &>/dev/null; then
    echo -e "${GREEN}✓ Usuario 'integra' ya existe${NC}"
else
    adduser --disabled-password --gecos "" integra
    usermod -aG docker integra
    usermod -aG sudo integra
    echo -e "${GREEN}✓ Usuario 'integra' creado${NC}"
fi

# =====================================================
# PASO 6: Crear estructura de directorios
# =====================================================
echo -e "\n${YELLOW}📁 Paso 5/6: Creando directorios...${NC}"

PROJECT_DIR="/home/integra/proyectos"
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/nginx/ssl"
mkdir -p "$PROJECT_DIR/nginx/logs"
mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"

chown -R integra:integra /home/integra
echo -e "${GREEN}✓ Directorios creados${NC}"

# =====================================================
# PASO 7: Configurar firewall
# =====================================================
echo -e "\n${YELLOW}🔥 Paso 6/6: Configurando firewall...${NC}"

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8443/tcp  # Admin panel

echo "y" | ufw enable
echo -e "${GREEN}✓ Firewall configurado${NC}"

# =====================================================
# RESUMEN
# =====================================================
echo -e "\n${GREEN}"
echo "╔════════════════════════════════════════════════════╗"
echo "║     ✅ INSTALACIÓN COMPLETADA                      ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}Próximos pasos:${NC}"
echo ""
echo "1. Subir el proyecto:"
echo -e "   ${YELLOW}scp -r proyectos/* integra@$(hostname -I | awk '{print $1}'):/home/integra/proyectos/${NC}"
echo ""
echo "2. Conectar como usuario integra:"
echo -e "   ${YELLOW}su - integra${NC}"
echo ""
echo "3. Configurar .env:"
echo -e "   ${YELLOW}cd /home/integra/proyectos${NC}"
echo -e "   ${YELLOW}cp .env.example .env${NC}"
echo -e "   ${YELLOW}nano .env${NC}"
echo ""
echo "4. Generar certificados SSL:"
echo -e "   ${YELLOW}chmod +x scripts/*.sh${NC}"
echo -e "   ${YELLOW}./scripts/generate-ssl.sh${NC}"
echo ""
echo "5. Levantar servicios:"
echo -e "   ${YELLOW}docker compose up -d --build${NC}"
echo ""
echo -e "${GREEN}IP del servidor: $(hostname -I | awk '{print $1}')${NC}"
echo ""
