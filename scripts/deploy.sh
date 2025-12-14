#!/bin/bash
# Quick start script for production deployment
# Usage: ./scripts/deploy.sh [production|staging]

set -e  # Exit on error

ENVIRONMENT=${1:-production}
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "🚀 Iniciando despliegue Integra - Ambiente: $ENVIRONMENT"
echo "=================================================="

# 1. Verificar requisitos
echo "✓ Verificando requisitos..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker no instalado"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose no instalado"; exit 1; }

# 2. Verificar .env
echo "✓ Verificando configuración..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "⚠️  IMPORTANTE: Edita $PROJECT_ROOT/.env con valores reales"
    exit 1
fi

# 3. Crear directorios necesarios
echo "✓ Creando directorios..."
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/data"

# 4. Build y start
echo "✓ Construyendo imágenes Docker..."
cd "$PROJECT_ROOT"
docker-compose build

echo "✓ Iniciando servicios..."
docker-compose up -d

# 5. Esperar a que PostgreSQL esté listo
echo "✓ Esperando a que PostgreSQL esté listo..."
for i in {1..30}; do
    if docker-compose exec -T db psql -U postgres -c "SELECT 1" >/dev/null 2>&1; then
        echo "✓ PostgreSQL está listo"
        break
    fi
    echo "  Intento $i/30..."
    sleep 2
done

# 6. Verificar estado
echo ""
echo "✓ Verificando estado de servicios..."
docker-compose ps

echo ""
echo "✅ Despliegue completado exitosamente"
echo "=================================================="
echo ""
echo "Acceso:"
echo "  App principal: http://localhost:8501"
echo "  Admin panel:   http://localhost:8502"
echo ""
echo "Para ver logs:"
echo "  docker-compose logs -f app"
echo ""
echo "Para detener:"
echo "  docker-compose down"
echo ""
