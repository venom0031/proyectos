#!/bin/bash
# =====================================================
# Script de Backup Automático de PostgreSQL
# Ejecutar con cron para backups diarios
# =====================================================

set -e

# Configuración
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${DB_CONTAINER:-integra_db}"
DB_NAME="${DB_NAME:-integra_rls}"
DB_USER="${DB_USER:-postgres}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/integra_${DATE}.sql.gz"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

log_info "Iniciando backup de base de datos..."
log_info "  - Contenedor: $CONTAINER_NAME"
log_info "  - Base de datos: $DB_NAME"
log_info "  - Archivo destino: $BACKUP_FILE"

# Realizar backup
if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "✅ Backup completado exitosamente"
    log_info "   Tamaño: $BACKUP_SIZE"
else
    log_error "❌ Error al crear backup"
    exit 1
fi

# Limpiar backups antiguos
log_info "Limpiando backups con más de $RETENTION_DAYS días..."
DELETED=$(find "$BACKUP_DIR" -name "integra_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
log_info "  - Eliminados: $DELETED archivos antiguos"

# Listar backups actuales
log_info "Backups disponibles:"
ls -lh "$BACKUP_DIR"/integra_*.sql.gz 2>/dev/null | tail -5 || echo "  (ninguno)"

# Verificar integridad del backup
log_info "Verificando integridad del backup..."
if gzip -t "$BACKUP_FILE" 2>/dev/null; then
    log_info "✅ Integridad verificada"
else
    log_error "❌ El archivo de backup está corrupto"
    exit 1
fi

log_info "=== Backup completado ==="
