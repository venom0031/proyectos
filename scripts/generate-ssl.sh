#!/bin/bash
# =====================================================
# Script para generar certificados SSL de desarrollo
# Ejecutar en el VPS antes de iniciar los servicios
# =====================================================

set -e

SSL_DIR="./nginx/ssl"

echo "🔐 Generando certificados SSL auto-firmados para desarrollo..."

# Crear directorio si no existe
mkdir -p "$SSL_DIR"

# Generar certificado auto-firmado (válido 365 días)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.crt" \
    -subj "/C=CL/ST=Chile/L=Santiago/O=Integra/CN=localhost"

# Establecer permisos seguros
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"

echo "✅ Certificados generados:"
echo "   - $SSL_DIR/server.crt"
echo "   - $SSL_DIR/server.key"
echo ""
echo "⚠️  NOTA: Estos son certificados AUTO-FIRMADOS para desarrollo."
echo "   Para producción, usa Let's Encrypt con certbot:"
echo "   certbot certonly --webroot -w /var/www/certbot -d tu-dominio.com"
