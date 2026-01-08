#!/bin/bash
# =====================================================
# Script de Restauración de Backup PostgreSQL
# =====================================================

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
CONTAINER_NAME="${DB_CONTAINER:-integra_db}"
DB_NAME="${DB_NAME:-integra_rls}"
DB_USER="${DB_USER:-postgres}"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo ""
    echo "Backups disponibles:"
    ls -lh "$BACKUP_DIR"/integra_*.sql.gz 2>/dev/null || echo "  (ninguno encontrado en $BACKUP_DIR)"
    exit 1
fi

BACKUP_FILE="$1"

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Archivo no encontrado: $BACKUP_FILE"
    exit 1
fi

log_warn "⚠️  ADVERTENCIA: Esto eliminará todos los datos actuales de la base de datos"
log_warn "   Base de datos: $DB_NAME"
log_warn "   Backup: $BACKUP_FILE"
echo ""
read -p "¿Estás seguro? (escribe 'RESTAURAR' para confirmar): " CONFIRM

if [ "$CONFIRM" != "RESTAURAR" ]; then
    log_info "Operación cancelada"
    exit 0
fi

log_info "Iniciando restauración..."

# Desconectar usuarios activos
log_info "Desconectando usuarios activos..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '$DB_NAME'
    AND pid <> pg_backend_pid();
" 2>/dev/null || true

# Eliminar y recrear base de datos
log_info "Recreando base de datos..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

# Restaurar backup
log_info "Restaurando datos desde backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"

log_info "✅ Restauración completada exitosamente"
