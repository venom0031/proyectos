# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración de PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'integra_rls'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
}

# Configuración de la aplicación
APP_CONFIG = {
    'session_timeout_minutes': int(os.getenv('SESSION_TIMEOUT', '60')),
    'page_title': 'Matriz Semanal — Integra SpA (RLS)',
    'page_layout': 'wide',
}

# Pool de conexiones
POOL_CONFIG = {
    'minconn': int(os.getenv('DB_POOL_MIN', '1')),
    'maxconn': int(os.getenv('DB_POOL_MAX', '10')),
}
