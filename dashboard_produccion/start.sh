#!/bin/bash

# Script de inicio para VPS (Linux/Unix)
# Este script inicia tanto el backend como el frontend

echo "🚀 Iniciando Dashboard de Producción Odoo..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
fi

# Instalar/actualizar dependencias
echo "📥 Verificando dependencias..."
pip install -r requirements.txt --quiet

# Crear directorios de logs si no existen
mkdir -p logs

# Iniciar backend con Gunicorn
echo "🔧 Iniciando backend API..."
gunicorn backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile logs/api-access.log \
    --error-logfile logs/api-error.log \
    --daemon

# Esperar a que el backend esté listo
sleep 3

# Iniciar frontend con Streamlit
echo "🎨 Iniciando dashboard frontend..."
streamlit run dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --logger.level warning \
    > logs/streamlit.log 2>&1 &

echo "✅ Servicios iniciados!"
echo ""
echo "📊 API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🎨 Dashboard: http://localhost:8501"
echo ""
echo "Para ver los logs:"
echo "  API: tail -f logs/api-access.log"
echo "  Dashboard: tail -f logs/streamlit.log"
echo ""
echo "Para detener los servicios:"
echo "  pkill -f gunicorn"
echo "  pkill -f streamlit"
