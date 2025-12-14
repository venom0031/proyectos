#!/bin/bash
# =====================================================
# Script de Despliegue VPS - Integra SpA
# =====================================================
# Uso: ./deploy-vps.sh [build|start|stop|restart|logs|status]
# =====================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar que docker-compose esté instalado
check_requirements() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose no está instalado"
        exit 1
    fi
}

# Verificar archivo .env
check_env() {
    if [ ! -f .env ]; then
        log_warn "Archivo .env no encontrado. Copiando desde .env.example..."
        cp .env.example .env
        log_warn "Por favor edita .env con tus credenciales antes de continuar"
        exit 1
    fi
}

# Comandos
do_build() {
    log_info "Construyendo imágenes Docker..."
    docker-compose build --no-cache
    log_info "Build completado!"
}

do_start() {
    log_info "Iniciando servicios..."
    docker-compose up -d
    sleep 5
    do_status
}

do_stop() {
    log_info "Deteniendo servicios..."
    docker-compose down
    log_info "Servicios detenidos"
}

do_restart() {
    log_info "Reiniciando servicios..."
    docker-compose restart
    sleep 5
    do_status
}

do_logs() {
    log_info "Mostrando logs (Ctrl+C para salir)..."
    docker-compose logs -f
}

do_status() {
    log_info "Estado de servicios:"
    echo ""
    docker-compose ps
    echo ""
    
    # Verificar healthchecks
    log_info "Verificando healthchecks..."
    for container in integra_db integra_app integra_admin; do
        if docker ps -q -f name=$container &> /dev/null; then
            health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "N/A")
            echo "  $container: $health"
        fi
    done
}

do_update() {
    log_info "Actualizando aplicación..."
    git pull origin main
    do_build
    do_restart
    log_info "Actualización completada!"
}

# Main
check_requirements
check_env

case "${1:-start}" in
    build)
        do_build
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    logs)
        do_logs
        ;;
    status)
        do_status
        ;;
    update)
        do_update
        ;;
    *)
        echo "Uso: $0 {build|start|stop|restart|logs|status|update}"
        exit 1
        ;;
esac
