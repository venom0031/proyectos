# Sistema Integra SpA - Gestión de Datos Ganaderos

Sistema de visualización y gestión de datos de producción lechera con Row-Level Security (RLS).

## 🚀 Inicio Rápido

### Requisitos
- Python 3.12+
- PostgreSQL 16+
- Docker (opcional, para producción)

### Instalación Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd streamlit_app

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales

# 5. Inicializar base de datos
cd scripts
.\init.ps1  # Windows
./init.sh   # Linux/Mac

# 6. Ejecutar aplicación
streamlit run modules/app_rls.py

# 7. Panel de administración (solo admin)
streamlit run admin_panel.py
```

## 📁 Estructura del Proyecto

```
streamlit_app/
├── modules/app_rls.py      # Aplicación principal (usuarios)
├── admin_panel.py          # Panel de administración
├── requirements.txt
├── .env.example
├── README.md
├── docker-compose.yml
│
├── modules/               # Módulos Python
│   ├── auth.py           # Autenticación
│   ├── ...
```

## 👥 Usuarios

### Desarrollo
- **Admin**: `admin` / `admin123`
- **Usuario 1**: `user_eduvigis` / `test123`
- **Usuario 2**: `user_lagos` / `test123`

### Producción
Crear usuarios desde el panel de administración.

## 🔐 Row-Level Security (RLS)

### Tablas SIN RLS (públicas)
- `datos_semanales` - Ranking visible para todos

### Tablas CON RLS (filtradas)
- `datos_diarios` - Solo datos de empresas asignadas
- `establecimientos` - Solo establecimientos de sus empresas
- `historico_mdat` - Solo histórico de sus empresas

## 📊 Panel de Administración

### Funciones
1. **Carga de Datos**
   - Upload de Reporte Semanal (Excel)
   - Upload de Histórico MDAT
   - Validación automática de estructura

2. **Gestión de Usuarios**
   - Crear/editar usuarios
   - Asignar empresas (RLS)
   - Gestión de permisos

3. **Gestión de Empresas**
   - Crear/editar empresas
   - Asignar establecimientos

4. **Logs**
   - Historial de cargas
   - Cambios en permisos

## 📤 Carga de Datos

### Reporte Semanal

**Estructura esperada:**
```
Empresa | Empresa_COD | Establecimiento | CATEGORIA | CONCEPTO | 27-09-2025 | 28-09-2025 | ...
```

**Proceso:**
1. Ir a Panel Admin
2. Sección "Carga de Datos"
3. Upload archivo Excel
4. Seleccionar tipo "Reporte Semanal"
5. Click "Procesar"
6. Verificar log de carga

### Histórico MDAT

**Estructura esperada:**
```
Establecimiento | N° Semana | Año | MDAT | Vacas en ordeña
```

**Nota:** Solo se carga una vez al inicio.

## 🐳 Despliegue (Desarrollo y Producción)

### Local (Desarrollo)

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env
# Editar .env con credenciales

# 4. Ejecutar aplicación
streamlit run modules/app_rls.py

# Panel admin (otra terminal)
streamlit run admin_panel.py
```

### Servidor (Producción con Docker)

**Requisitos previos:**
- Docker y Docker Compose instalados
- Variables de entorno configuradas en `.env`

```bash
# 1. Construir e iniciar servicios
docker-compose up -d

# 2. Ver logs en tiempo real
docker-compose logs -f app

# 3. Detener servicios
docker-compose down
```

**Acceso:**
- App principal: `http://tu-servidor.com:8501`
- Panel admin: `http://tu-servidor.com:8502`
- PostgreSQL: Puerto 5432 (solo acceso interno)

**Características del despliegue Docker:**
- ✅ wkhtmltopdf pre-instalado en la imagen
- ✅ PostgreSQL con volumen persistente
- ✅ Healthchecks automáticos
- ✅ Reinicio automático si falla

**Escalado a producción:**
1. Cambiar `DB_PASSWORD` en `.env` a contraseña segura
2. Usar Nginx/Traefik como reverse proxy con SSL
3. Configurar backups automáticos del volumen `postgres_data`
4. Monitorear con herramientas como Prometheus/Grafana

## 🔧 Configuración

### Variables de Entorno (`.env`)

```env
# ============================================
# Base de Datos
# ============================================
DB_HOST=localhost          # 'db' si usas Docker
DB_PORT=5432
DB_NAME=integra_rls
DB_USER=postgres
DB_PASSWORD=tu_password_segura

# Pool de Conexiones
DB_POOL_MIN=1
DB_POOL_MAX=10

# Sesión
SESSION_TIMEOUT=60

# ============================================
# PDF Export Configuration (NUEVO)
# ============================================
# Ruta absoluta a wkhtmltopdf (dejar en blanco para auto-detección)
WKHTMLTOPDF_PATH=
# Fallback a HTML si wkhtmltopdf no está disponible
PDF_FALLBACK_TO_HTML=true
```

### Instalación de wkhtmltopdf

**Windows (Recomendado: Chocolatey)**
```powershell
choco install wkhtmltopdf -y
```

**Windows (Manual)**
1. Descargar desde https://wkhtmltopdf.org/
2. Instalar normalmente
3. Verificar PATH o usar WKHTMLTOPDF_PATH

**Linux (Debian/Ubuntu)**
```bash
apt-get update
apt-get install -y wkhtmltopdf xfonts-75dpi xfonts-96dpi xfonts-base xfonts-encodings libfontconfig1 fontconfig
```

**macOS**
```bash
brew install wkhtmltopdf
```

**Verificar instalación:**
```bash
wkhtmltopdf --version
```

Si ves versión → ✅ Correctamente instalado
Si ves error → Configura WKHTMLTOPDF_PATH en `.env` o reinicia terminal

## 🛠️ Desarrollo

### Ejecutar tests
```bash
python -m pytest tests/
```

### Linting
```bash
flake8 modules/
```

## 📝 Notas de Producción

1. **Backups**: Configurar backup automático diario
2. **SSL**: Usar certificado Let's Encrypt
3. **Firewall**: Solo puertos 80, 443, 5432 (interno)
4. **Monitoring**: Configurar logs y alertas
5. **Updates**: Probar en staging primero

## 🐛 Troubleshooting

### Error de conexión PostgreSQL
- Verificar que PostgreSQL está corriendo
- Checar credenciales en `.env`
- Verificar firewall

### Error de encoding UTF-8
- Ver `INSTALACION.md` para soluciones Windows

### RLS no filtra correctamente
- Verificar asignación usuario-empresa en BD
- Checar que `is_admin` está correcto

## 📊 PDF Export (Nueva Funcionalidad)

La aplicación permite exportar la matriz a **PDF con estilos personalizados** (fondo blanco, bordes verdes).

### Requisitos

1. **pdfkit** (Python) - Ya incluido en `requirements.txt`
2. **wkhtmltopdf** (Binario) - Ver sección "Instalación de wkhtmltopdf" arriba

### Cómo usar

1. Abre la app (`app.py` o `app_rls.py`)
2. Navega a la pestaña "Matriz Semanal"
3. Click en "📄 Descargar matriz en PDF"
4. Descarga automática

### Troubleshooting PDF

**"❌ pdfkit no está instalado"**
```bash
pip install pdfkit jinja2
```

**"❌ wkhtmltopdf no está disponible"**
- Instala wkhtmltopdf (ver sección arriba)
- O configura `WKHTMLTOPDF_PATH` en `.env`

**Fallback a HTML**
- Si no está disponible wkhtmltopdf, la app ofrece descargar en HTML
- Configurable con `PDF_FALLBACK_TO_HTML=true` en `.env`

## 📞 Soporte

Para issues y preguntas: [GitHub Issues]

## 📄 Licencia

Proprietary - Integra SpA © 2024