# ============================================
# CONFIGURACIÓN CENTRAL DE LA APLICACIÓN
# ============================================
import os
import sys
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'integra_rls'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
}

# Pool de conexiones
POOL_CONFIG = {
    'minconn': int(os.getenv('DB_POOL_MIN', '2')),
    'maxconn': int(os.getenv('DB_POOL_MAX', '20')),
}

# ============================================
# CONFIGURACIÓN DE REDIS (CACHE)
# ============================================
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'enabled': os.getenv('REDIS_ENABLED', 'true').lower() == 'true',
}

# ============================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================
APP_CONFIG = {
    'session_timeout_minutes': int(os.getenv('SESSION_TIMEOUT', '60')),
    'page_title': 'Matriz Semanal — Integra SpA (RLS)',
    'page_layout': 'wide',
    'environment': os.getenv('ENVIRONMENT', 'development'),
}

# ============================================
# CONFIGURACIÓN DE LOGGING
# ============================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', 'standard')  # 'standard' o 'json'

def setup_logging():
    """Configura el sistema de logging centralizado."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # Formato según entorno
    if LOG_FORMAT == 'json' or APP_CONFIG['environment'] == 'production':
        # Formato JSON para producción (mejor para agregación de logs)
        try:
            import json
            
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_data = {
                        'timestamp': self.formatTime(record),
                        'level': record.levelname,
                        'logger': record.name,
                        'message': record.getMessage(),
                        'module': record.module,
                        'function': record.funcName,
                        'line': record.lineno,
                    }
                    if record.exc_info:
                        log_data['exception'] = self.formatException(record.exc_info)
                    return json.dumps(log_data)
            
            formatter = JSONFormatter()
        except Exception:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    else:
        # Formato estándar para desarrollo
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configurar handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Limpiar handlers existentes
    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    
    # Silenciar logs de librerías externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('streamlit').setLevel(logging.WARNING)
    
    return root_logger


# Inicializar logging al importar
logger = setup_logging()
