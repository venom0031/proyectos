# Instalación de Dependencias para Reporteria
# Servidor: debian@51.222.87.227

## 📋 Requisitos

Reporteria requiere:
- **PostgreSQL 16+** (Base de datos principal)
- **Redis** (Cache y sesiones)
- **Python 3.13+** (Ya instalado ✅)
- **wkhtmltopdf** (Exportar PDFs)

---

## 🗄️ Instalar PostgreSQL 16

### 1. Agregar repositorio oficial de PostgreSQL

```bash
# Instalar certificado
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

# Actualizar repositorios
sudo apt update
```

### 2. Instalar PostgreSQL 16

```bash
sudo apt install -y postgresql-16 postgresql-contrib-16
```

### 3. Verificar instalación

```bash
# Ver versión
psql --version
# Debe mostrar: psql (PostgreSQL) 16.x

# Ver estado del servicio
sudo systemctl status postgresql
```

### 4. Configurar PostgreSQL

```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Dentro de psql:
# Cambiar contraseña del usuario postgres (IMPORTANTE)
ALTER USER postgres WITH PASSWORD 'tu_password_super_segura';

# Salir
\q
```

### 5. Crear base de datos para Reporteria

```bash
# Crear base de datos
sudo -u postgres createdb integra_rls

# Verificar que se creó
sudo -u postgres psql -l | grep integra
```

### 6. Inicializar esquema

```bash
cd /home/debian/clientes/integra/reporteria

# Ejecutar script de inicialización
sudo -u postgres psql -d integra_rls -f db/schema/init_db.sql

# Cargar datos de ejemplo (OPCIONAL)
sudo -u postgres psql -d integra_rls -f db/fixtures/load_sample.sql
```

---

## 🔴 Instalar Redis

### 1. Instalar Redis Server

```bash
sudo apt install -y redis-server
```

### 2. Configurar Redis

```bash
# Editar configuración
sudo nano /etc/redis/redis.conf

# Cambiar estas líneas:
# supervised no  →  supervised systemd
# bind 127.0.0.1 ::1  (dejar como está - solo localhost)
```

### 3. Reiniciar Redis

```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### 4. Verificar Redis

```bash
# Ver estado
sudo systemctl status redis-server

# Test de conexión
redis-cli ping
# Debe responder: PONG

# Ver información
redis-cli info server
```

---

## 📄 Instalar wkhtmltopdf (Para PDFs)

```bash
# Instalar dependencias
sudo apt install -y xfonts-75dpi xfonts-base xfonts-encodings fontconfig libfontconfig1

# Instalar wkhtmltopdf
sudo apt install -y wkhtmltopdf

# Verificar instalación
wkhtmltopdf --version
```

---

## 🔥 Configurar Firewall (UFW)

```bash
# Permitir puertos de Reporteria
sudo ufw allow 8502/tcp comment "INTEGRA Reporteria App"
sudo ufw allow 8503/tcp comment "INTEGRA Reporteria Admin"

# PostgreSQL (solo localhost - NO exponer)
# Redis (solo localhost - NO exponer)

# Verificar reglas
sudo ufw status numbered
```

---

## ✅ Verificación Final

### PostgreSQL
```bash
# Conectar a la base de datos
sudo -u postgres psql -d integra_rls

# Ver tablas (después de inicializar esquema)
\dt

# Salir
\q
```

### Redis
```bash
redis-cli ping
# Respuesta: PONG

redis-cli
# Dentro:
SET test "hola"
GET test
# Debe mostrar: "hola"
EXIT
```

### Resumen de servicios
```bash
sudo systemctl status postgresql
sudo systemctl status redis-server
```

---

## 📝 Configurar .env de Reporteria

Después de instalar todo:

```bash
cd /home/debian/clientes/integra/reporteria

# Copiar template
cp .env.template .env

# Editar con credenciales reales
nano .env
```

Configuración mínima en `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=integra_rls
DB_USER=postgres
DB_PASSWORD=tu_password_super_segura  # ⚠️ La que configuraste arriba

DB_POOL_MIN=1
DB_POOL_MAX=10

SESSION_TIMEOUT=60

WKHTMLTOPDF_PATH=
PDF_FALLBACK_TO_HTML=true
```

---

## 🚀 Iniciar Servicios de Reporteria

```bash
# Habilitar en el arranque
sudo systemctl enable integra-reporteria
sudo systemctl enable integra-reporteria-admin

# Iniciar servicios
sudo systemctl start integra-reporteria
sudo systemctl start integra-reporteria-admin

# Verificar estado
sudo systemctl status integra-reporteria
sudo systemctl status integra-reporteria-admin
```

---

## 🌐 Verificar Acceso

```bash
# Desde el servidor
curl -I http://localhost:8502  # App principal
curl -I http://localhost:8503  # Admin panel

# Desde tu PC (Windows)
# http://51.222.87.227:8502
# http://51.222.87.227:8503
```

---

## 📊 Monitoreo

### Ver logs en tiempo real
```bash
# App principal
sudo journalctl -u integra-reporteria -f

# Admin panel
sudo journalctl -u integra-reporteria-admin -f

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Redis
sudo tail -f /var/log/redis/redis-server.log
```

### Ver recursos
```bash
# PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname='integra_rls';"

# Redis
redis-cli info memory
redis-cli info stats
```

---

## 🔧 Troubleshooting

### PostgreSQL no acepta conexiones
```bash
# Ver logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Reiniciar servicio
sudo systemctl restart postgresql
```

### Redis no responde
```bash
# Ver logs
sudo tail -f /var/log/redis/redis-server.log

# Reiniciar
sudo systemctl restart redis-server
```

### Reporteria no inicia
```bash
# Ver logs detallados
sudo journalctl -u integra-reporteria -n 100 --no-pager

# Test manual
cd /home/debian/clientes/integra/reporteria
source venv/bin/activate
streamlit run modules/app.py --server.port=8502
```

---

## 💾 Backup Automático

### Script de backup diario
```bash
# Crear script
sudo nano /usr/local/bin/backup-integra-db.sh
```

Contenido del script:
```bash
#!/bin/bash
BACKUP_DIR="/home/debian/clientes/integra/reporteria/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U postgres integra_rls > "$BACKUP_DIR/integra_rls_$DATE.sql"
# Mantener solo últimos 7 días
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
```

```bash
# Dar permisos
sudo chmod +x /usr/local/bin/backup-integra-db.sh

# Agregar a crontab
sudo crontab -e
# Agregar:
0 2 * * * /usr/local/bin/backup-integra-db.sh
```

---

## ✅ Checklist de Instalación

- [ ] PostgreSQL 16 instalado
- [ ] Redis instalado
- [ ] wkhtmltopdf instalado
- [ ] Base de datos `integra_rls` creada
- [ ] Esquema inicializado
- [ ] Contraseña de postgres configurada
- [ ] `.env` configurado con credenciales
- [ ] Firewall configurado (puertos 8502, 8503)
- [ ] Servicios systemd habilitados
- [ ] Servicios iniciados correctamente
- [ ] Acceso web verificado
- [ ] Backup automático configurado

---

**¡Listo para usar Reporteria! 🎉**
