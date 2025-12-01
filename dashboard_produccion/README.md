# Dashboard de Produccion Odoo

Dashboard modular para visualizacion y analisis de ordenes de fabricacion de Odoo con backend FastAPI y frontend Streamlit.

##  Caracteristicas

-  **Busqueda de OFs**: Busqueda por rango de fechas
-  **KPIs de Produccion**: Rendimiento, eficiencia, consumo de MP
-  **Detalle Completo**: Componentes, subproductos, detenciones y horas de consumo
-  **Interfaz Premium**: Dashboard con diseno moderno y dark mode
-  **Arquitectura Modular**: Codigo organizado y escalable para nuevos dashboards

##  Requisitos

- Python 3.8+
- Acceso a una instancia de Odoo (16+)
- Credenciales de usuario de Odoo

##  Instalacion

### 1. Clonar o Descargar el Proyecto

```bash
git clone <tu-repositorio>
cd DASHNBOARDS
```

### 2. Crear Entorno Virtual

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y configura tus credenciales:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus datos:

```env
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=tu-base-de-datos
ODOO_USER=tu-usuario@email.com
ODOO_PASSWORD=tu-contrasena
API_URL=http://127.0.0.1:8000
```

##  Ejecucion Local (Desarrollo)

### Opcion 1: Scripts de Inicio Automaticos

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### Opcion 2: Iniciar Servicios Manualmente

#### Backend (Terminal 1)
```bash
uvicorn backend.main:app --reload
```

#### Frontend (Terminal 2)
```bash
streamlit run dashboard.py
```

### Acceso

- **API Backend**: http://localhost:8000
- **Documentacion API**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501

##  Deployment a VPS (Produccion)

### 1. Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python y pip
sudo apt install python3 python3-pip python3-venv -y

# Clonar el proyecto
git clone <tu-repositorio>
cd DASHNBOARDS
```

### 2. Configurar el Entorno

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
nano .env  # Editar con tus credenciales
```

### 3. Iniciar Servicios

```bash
# Dar permisos de ejecucion al script
chmod +x start.sh

# Iniciar servicios
./start.sh
```

### 3.1 Notas de seguridad y configuracion

- El dashboard consume la API desde `dashboard.py` en la raiz (scripts `start.sh` y `start.bat` ya apuntan ahi).
- Define la variable de entorno `SETTINGS_TOKEN` en el backend y en el entorno del frontend; es requerida para acceder a los endpoints y pantalla de configuracion.
- Mantener las credenciales de Odoo solo en variables de entorno o en `config.json` con acceso restringido en el servidor.

### 4. Configurar como Servicio (Opcional)

Para que los servicios se inicien automaticamente:

**Backend (API):**
```bash
sudo nano /etc/systemd/system/odoo-api.service
```

```ini
[Unit]
Description=Odoo Dashboard API
After=network.target

[Service]
Type=simple
User=tu-usuario
WorkingDirectory=/ruta/a/DASHNBOARDS
Environment="PATH=/ruta/a/DASHNBOARDS/venv/bin"
ExecStart=/ruta/a/DASHNBOARDS/venv/bin/gunicorn backend.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Frontend (Dashboard):**
```bash
sudo nano /etc/systemd/system/odoo-dashboard.service
```

```ini
[Unit]
Description=Odoo Dashboard Frontend
After=network.target odoo-api.service

[Service]
Type=simple
User=tu-usuario
WorkingDirectory=/ruta/a/DASHNBOARDS
Environment="PATH=/ruta/a/DASHNBOARDS/venv/bin"
ExecStart=/ruta/a/DASHNBOARDS/venv/bin/streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar servicios:
```bash
sudo systemctl daemon-reload
sudo systemctl enable odoo-api odoo-dashboard
sudo systemctl start odoo-api odoo-dashboard
```

### 5. Configurar Nginx (Opcional)

Para servir a traves de un dominio:

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/odoo-dashboard
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Dashboard
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/odoo-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

##  Estructura del Proyecto

```
DASHNBOARDS/
 backend/
    config/
       settings.py         # Configuracion centralizada
    core/
       odoo_connection.py  # Conexion a Odoo
    routers/
       of_routes.py        # Endpoints de API
    services/
       of_service.py       # Logica de negocio
    utils/
       helpers.py          # Funciones auxiliares
    main.py                 # Aplicacion FastAPI
 frontend/
    components/
       kpi_cards.py        # Componentes de KPIs
       charts.py           # Graficos
       tables.py           # Tablas
    services/
       api_client.py       # Cliente API
    config/
       settings.py         # Configuracion UI
    dashboard.py            # Dashboard modular
 dashboard.py                # Punto de entrada principal
 requirements.txt            # Dependencias
 .env.example                # Template de configuracion
 start.sh                    # Script de inicio (Linux)
 start.bat                   # Script de inicio (Windows)
 README.md                   # Este archivo
```

##  Anadir Nuevos Dashboards

La estructura modular permite anadir facilmente nuevos dashboards. Ejemplo para un dashboard de stock:

### 1. Crear Router en el Backend

```python
# backend/routers/stock_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/stock", tags=["Stock"])

@router.get("/ubicaciones")
def get_ubicaciones():
    # Tu logica aqui
    pass
```

### 2. Registrar Router

```python
# backend/main.py
from backend.routers import stock_routes

app.include_router(stock_routes.router)
```

### 3. Crear Dashboard Frontend

```python
# frontend/stock_dashboard.py
import streamlit as st
from frontend.services.api_client import api_client

st.title(" Dashboard de Stock")
# Tu UI aqui
```

### 4. Crear Punto de Entrada

```python
# stock.py (en la raiz)
from frontend.stock_dashboard import *
```

Ejecutar: `streamlit run stock.py`

##  API Documentation

Una vez iniciado el backend, puedes acceder a la documentacion interactiva de la API en:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

##  Troubleshooting

### Error de Conexion a Odoo

Verifica que:
- Las credenciales en `.env` sean correctas
- La URL de Odoo sea accesible
- El usuario tenga permisos suficientes

### Puerto en Uso

Si ves errores de puerto en uso:

```bash
# Para ver que proceso usa el puerto 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Matar el proceso
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # Linux/Mac
```

### Limpiar Cache

Si ves datos antiguos, limpia el cache desde el boton " Recargar / Limpiar Cache" en el sidebar.

##  Licencia

Este proyecto es de uso interno. Todos los derechos reservados.

##  Soporte

Para soporte o preguntas, contacta al equipo de desarrollo.
