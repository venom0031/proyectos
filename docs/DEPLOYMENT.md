# Guía de Despliegue a Producción

Esta guía cubre cómo desplegar la aplicación Integra en un servidor de producción usando Docker.

## 1. Preparación del Servidor

### Requisitos del Sistema
- **SO**: Linux (recomendado: Ubuntu 20.04+ o Debian 11+)
- **CPU**: 2+ cores
- **RAM**: 4 GB mínimo
- **Almacenamiento**: 50+ GB para base de datos
- **Docker**: 20.10+
- **Docker Compose**: 1.29+

### Instalación de Docker y Docker Compose

```bash
# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker (evita sudo en cada comando)
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

## 2. Preparar la Aplicación

```bash
# Clonar repositorio
git clone <repo-url> /opt/integra
cd /opt/integra

# Crear archivo .env para producción
cp .env.example .env

# Editar .env con valores de producción
nano .env
```

### Configuración de `.env` para Producción

```env
# Base de Datos
DB_HOST=db
DB_PORT=5432
DB_NAME=integra_rls
DB_USER=postgres
DB_PASSWORD=TU_PASSWORD_SEGURA_AQUI_MIN_20_CHARS

# Pool de conexiones (ajustar según carga)
DB_POOL_MIN=2
DB_POOL_MAX=20

# Sesión
SESSION_TIMEOUT=120

# PDF Configuration
WKHTMLTOPDF_PATH=/usr/bin/wkhtmltopdf
PDF_FALLBACK_TO_HTML=true

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
```

⚠️ **Importante**: Cambiar `DB_PASSWORD` a una contraseña segura (mínimo 20 caracteres, números, símbolos).

## 3. Configurar Persistencia de Datos

```bash
# Crear directorio para volumenes de Docker
sudo mkdir -p /mnt/integra-data/postgres
sudo mkdir -p /mnt/integra-data/logs

# Ajustar permisos
sudo chown -R 999:999 /mnt/integra-data/postgres  # UID de usuario postgres en image
sudo chmod 750 /mnt/integra-data/postgres

# Editar docker-compose.yml si es necesario cambiar rutas
# (por defecto usa volumes docker manejados)
```

## 4. Iniciar Servicios

```bash
cd /opt/integra

# Construir imagen (primera vez)
docker-compose build

# Iniciar servicios en background
docker-compose up -d

# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs -f app
```

**Esperado**: Ver ambos servicios en estado `Up` y sin errores.

## 5. Verificar Funcionamiento

```bash
# Test de conectividad a PostgreSQL
docker-compose exec db psql -U postgres -c "SELECT version();"

# Test de aplicación Streamlit
curl http://localhost:8501

# Ver logs de inicialización
docker-compose logs app | tail -50
```

## 6. Configurar Reverse Proxy (Nginx + SSL)

### Instalar Nginx

```bash
sudo apt-get install -y nginx
sudo systemctl enable nginx
```

### Configurar Virtual Host

Crear archivo `/etc/nginx/sites-available/integra`:

```nginx
upstream streamlit_app {
    server 127.0.0.1:8501;
}

upstream streamlit_admin {
    server 127.0.0.1:8502;
}

server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;
    
    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;
    
    # Certificados SSL (ver paso 7)
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    
    # Seguridad SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Logs
    access_log /var/log/nginx/integra_access.log;
    error_log /var/log/nginx/integra_error.log;
    
    # Limites
    client_max_body_size 100M;
    
    # App principal
    location / {
        proxy_pass http://streamlit_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Admin panel
    location /admin {
        proxy_pass http://streamlit_admin/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Activar Virtual Host

```bash
sudo ln -s /etc/nginx/sites-available/integra /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar sintaxis
sudo systemctl restart nginx
```

## 7. Certificado SSL (Let's Encrypt)

```bash
# Instalar certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot certonly --nginx -d tu-dominio.com -d www.tu-dominio.com

# Renovación automática (ya configurada)
sudo systemctl enable certbot.timer
```

## 8. Backups Automáticos

Crear script `/opt/integra/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/mnt/integra-data/backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/postgres_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

# Backup de PostgreSQL
docker-compose exec -T db pg_dump -U postgres integra_rls > $BACKUP_FILE
gzip $BACKUP_FILE

# Mantener solo últimos 30 días
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completado: $BACKUP_FILE.gz"
```

Hacer ejecutable y agregar a cron:

```bash
chmod +x /opt/integra/backup.sh
sudo crontab -e

# Agregar línea (backup diario a las 2 AM):
0 2 * * * /opt/integra/backup.sh >> /var/log/integra-backup.log 2>&1
```

## 9. Monitoreo

### Healthcheck

Los servicios incluyen healthchecks automáticos. Verificar:

```bash
docker-compose ps
```

El estado debe ser `healthy` (después de 30 segundos).

### Logs

```bash
# Logs de la app en tiempo real
docker-compose logs -f app

# Últimas 100 líneas
docker-compose logs --tail=100 app

# Logs de PostgreSQL
docker-compose logs db
```

### Alertas (Opcional)

Considerar herramientas como:
- **Sentry** (error tracking)
- **Datadog** (monitoring)
- **New Relic** (APM)

## 10. Mantenimiento

### Actualizar Aplicación

```bash
cd /opt/integra

# Descargar cambios
git pull origin main

# Reconstruir imagen
docker-compose build

# Reiniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### Actualizar Dependencias Python

Modificar `requirements.txt` en el repositorio y ejecutar:

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Limpiar Recursos

```bash
# Eliminar contenedores detenidos
docker container prune

# Eliminar imágenes no usadas
docker image prune

# Eliminar volúmenes no usados
docker volume prune
```

## 11. Troubleshooting

### App no carga

```bash
# Verificar contenedor está running
docker-compose ps

# Ver logs de error
docker-compose logs app

# Verificar puerto 8501 está escuchando
netstat -tlnp | grep 8501
```

### Base de datos no conecta

```bash
# Verificar contenedor PostgreSQL
docker-compose ps db

# Testear conexión
docker-compose exec db psql -U postgres -c "SELECT 1;"

# Ver logs
docker-compose logs db
```

### PDF no genera

```bash
# Verificar wkhtmltopdf en la image
docker-compose exec app which wkhtmltopdf

# Probar versión
docker-compose exec app wkhtmltopdf --version
```

### Permisos en archivos

```bash
# Si hay error de permisos
sudo chown -R 1000:1000 /mnt/integra-data/
```

## 12. Seguridad

- ✅ Cambiar contraseña de PostgreSQL en `.env`
- ✅ Usar HTTPS (Let's Encrypt)
- ✅ Firewall: Abrir solo puertos 80, 443
- ✅ SSH key-based auth (no password)
- ✅ Backups encriptados
- ✅ Logs centralizados
- ✅ Actualizaciones de seguridad regulares

## 13. Escalado Futuro

Para aplicaciones con más usuarios:

1. **Load Balancer**: Nginx upstream con múltiples app instances
2. **Cache**: Redis para sesiones
3. **Database**: Replica de PostgreSQL
4. **CDN**: CloudFlare para static assets
5. **Object Storage**: S3 para backups

---

**Soporte**: Para preguntas o issues, contactar al equipo de desarrollo.
