# 🚀 Guía de Despliegue - Debian 13 (Trixie)

## Requisitos previos
- VPS con Debian 13 (mínimo 2GB RAM, 20GB disco)
- Acceso SSH como root o usuario con sudo
- Dominio apuntando al VPS (opcional, pero recomendado para SSL)

---

## 📋 Paso 1: Preparar el servidor

```bash
# Conectar al VPS
ssh root@TU_IP_VPS

# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias básicas
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
    lsb-release
```

---

## 🐳 Paso 2: Instalar Docker

```bash
# Agregar repositorio oficial de Docker
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalación
docker --version
docker compose version

# Habilitar Docker al inicio
systemctl enable docker
systemctl start docker
```

---

## 👤 Paso 3: Crear usuario para la app (opcional pero recomendado)

```bash
# Crear usuario
adduser integra
usermod -aG docker integra
usermod -aG sudo integra

# Cambiar a ese usuario
su - integra
```

---

## 📁 Paso 4: Subir el proyecto

### Opción A: Desde Git (recomendado)
```bash
cd /home/integra
git clone https://TU_REPO_GIT/reporteria-integra.git
cd reporteria-integra/proyectos
```

### Opción B: Subir con SCP (desde tu PC Windows)
```powershell
# En PowerShell de Windows
scp -r "C:\Users\Miguel\Desktop\reporteria-integra\proyectos" integra@TU_IP_VPS:/home/integra/
```

### Opción C: Subir con rsync (más eficiente)
```powershell
# Instalar rsync en Windows (via Git Bash o WSL)
rsync -avz --progress -e ssh "C:/Users/Miguel/Desktop/reporteria-integra/proyectos/" integra@TU_IP_VPS:/home/integra/proyectos/
```

---

## 🔐 Paso 5: Configurar variables de entorno

```bash
cd /home/integra/proyectos

# Copiar template
cp .env.example .env

# Editar con credenciales de producción
nano .env
```

**Contenido de `.env` para producción:**
```env
# Base de datos - CAMBIAR ESTAS CREDENCIALES
DB_HOST=db
DB_PORT=5432
DB_NAME=integra_rls
DB_USER=integra_prod
DB_PASSWORD=TU_PASSWORD_SEGURO_AQUI

# Pool de conexiones
DB_POOL_MIN=2
DB_POOL_MAX=20

# Sesión
SESSION_TIMEOUT=60

# Seguridad
SECRET_KEY=genera_una_clave_larga_aleatoria_aqui
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Grafana (opcional)
GRAFANA_USER=admin
GRAFANA_PASSWORD=TU_PASSWORD_GRAFANA
```

> 💡 **Generar SECRET_KEY:**
> ```bash
> openssl rand -hex 32
> ```

---

## 🔒 Paso 6: Generar certificados SSL

```bash
cd /home/integra/proyectos

# Crear directorios
mkdir -p nginx/ssl nginx/logs backups logs

# Dar permisos de ejecución a scripts
chmod +x scripts/*.sh

# Generar certificados auto-firmados (para pruebas)
./scripts/generate-ssl.sh

# Para producción con Let's Encrypt, ver sección "SSL con Let's Encrypt"
```

---

## 🚀 Paso 7: Construir y levantar servicios

```bash
cd /home/integra/proyectos

# Construir imágenes
docker compose build

# Levantar servicios en background
docker compose up -d

# Ver logs
docker compose logs -f

# Verificar que todo esté corriendo
docker compose ps
```

**Salida esperada:**
```
NAME               STATUS
integra_db         healthy
integra_redis      healthy
integra_app        running
integra_admin      running
integra_nginx      running
```

---

## 🗄️ Paso 8: Inicializar base de datos

```bash
# Esperar a que PostgreSQL esté listo (30 segundos aprox)
sleep 30

# Ejecutar schema inicial
docker exec -i integra_db psql -U integra_prod -d integra_rls < db/schema/schema.sql

# Ejecutar migraciones de optimización
docker exec -i integra_db psql -U integra_prod -d integra_rls < db/migrations/optimize_for_vps.sql
docker exec -i integra_db psql -U integra_prod -d integra_rls < db/migrations/maintenance_config.sql

# Verificar
docker exec integra_db psql -U integra_prod -d integra_rls -c "SELECT * FROM v_data_summary;"
```

---

## 👥 Paso 9: Crear usuario admin

```bash
# Generar hash de password
docker exec integra_app python -c "import bcrypt; print(bcrypt.hashpw(b'TU_PASSWORD', bcrypt.gensalt()).decode())"

# Insertar usuario admin (reemplazar el hash)
docker exec integra_db psql -U integra_prod -d integra_rls -c "
INSERT INTO usuarios (username, password_hash, nombre_completo, email, is_admin, activo)
VALUES ('admin', 'PEGA_EL_HASH_AQUI', 'Administrador', 'admin@tuempresa.com', true, true);
"
```

---

## 🔥 Paso 10: Configurar firewall

```bash
# Configurar UFW
ufw default deny incoming
ufw default allow outgoing

# SSH
ufw allow 22/tcp

# HTTP y HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Admin panel (opcional, solo si necesitas acceso directo)
ufw allow 8443/tcp

# Habilitar firewall
ufw enable
ufw status
```

---

## ⏰ Paso 11: Configurar backups automáticos

```bash
# Editar crontab
crontab -e

# Agregar estas líneas:
# Backup diario a las 3AM
0 3 * * * /home/integra/proyectos/scripts/backup-db.sh >> /var/log/integra-backup.log 2>&1

# Backup semanal domingo 2AM (30 días retención)
0 2 * * 0 RETENTION_DAYS=30 /home/integra/proyectos/scripts/backup-db.sh >> /var/log/integra-backup.log 2>&1

# Mantenimiento DB a las 4AM
0 4 * * * docker exec integra_db psql -U integra_prod -d integra_rls -c "SELECT run_maintenance();" >> /var/log/integra-maintenance.log 2>&1
```

---

## 🌐 Paso 12: Configurar dominio (DNS)

En tu proveedor de DNS, agregar:
```
A     @       TU_IP_VPS
A     www     TU_IP_VPS
A     admin   TU_IP_VPS  (opcional)
```

---

## 🔒 SSL con Let's Encrypt (Producción)

```bash
# Instalar Certbot
apt install -y certbot

# Detener nginx temporalmente
docker compose stop nginx

# Obtener certificado
certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com

# Copiar certificados
cp /etc/letsencrypt/live/tu-dominio.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/tu-dominio.com/privkey.pem nginx/ssl/key.pem

# Reiniciar nginx
docker compose start nginx

# Configurar renovación automática
echo "0 0 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/tu-dominio.com/*.pem /home/integra/proyectos/nginx/ssl/ && docker compose restart nginx" | crontab -
```

---

## ✅ Verificación final

```bash
# Ver estado de servicios
docker compose ps

# Ver logs
docker compose logs --tail=50

# Probar conectividad
curl -k https://localhost
curl -k https://localhost:8443

# Ver salud de la BD
docker exec integra_db psql -U integra_prod -d integra_rls -c "SELECT * FROM v_database_health;"
```

---

## 🔗 URLs de acceso

| Servicio | URL |
|----------|-----|
| App Principal | `https://tu-dominio.com` |
| Admin Panel | `https://tu-dominio.com:8443` |
| Grafana | `http://tu-dominio.com:3000` (si instalaste monitoreo) |
| Prometheus | `http://tu-dominio.com:9090` (si instalaste monitoreo) |

---

## 📊 Monitoreo (Opcional)

```bash
# Levantar stack de monitoreo
docker compose -f docker-compose.monitoring.yml up -d

# Acceder a Grafana
# URL: http://tu-dominio.com:3000
# Usuario: admin
# Password: (el que pusiste en .env)
```

---

## 🛠️ Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs -f app

# Reiniciar un servicio
docker compose restart app

# Actualizar código
cd /home/integra/proyectos
git pull
docker compose build
docker compose up -d

# Backup manual
./scripts/backup-db.sh

# Entrar al contenedor de la app
docker exec -it integra_app bash

# Entrar a PostgreSQL
docker exec -it integra_db psql -U integra_prod -d integra_rls
```

---

## 🚨 Troubleshooting

### Error: Puerto 80/443 ocupado
```bash
# Ver qué está usando el puerto
lsof -i :80
# Detener el servicio que lo usa
systemctl stop apache2  # o nginx si hay otro instalado
```

### Error: Permisos en volúmenes
```bash
# Dar permisos al usuario integra
chown -R 1000:1000 /home/integra/proyectos/logs
chown -R 1000:1000 /home/integra/proyectos/data
chown -R 1000:1000 /home/integra/proyectos/backups
```

### Error: Base de datos no inicializada
```bash
# Borrar volumen y reiniciar
docker compose down -v
docker compose up -d
# Esperar 30 seg y re-ejecutar schema
```

### Ver logs de error específicos
```bash
docker compose logs app 2>&1 | grep -i error
docker compose logs nginx 2>&1 | grep -i error
```
