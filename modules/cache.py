# =====================================================
# MÓDULO DE CACHE CON REDIS
# Cache para consultas frecuentes y datos de sesión
# =====================================================

import os
import json
import logging
import hashlib
from typing import Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Configuración de Redis
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'decode_responses': True,
}

# TTL por defecto (en segundos)
DEFAULT_TTL = 300  # 5 minutos
QUERY_TTL = 600    # 10 minutos para queries
SESSION_TTL = 3600 # 1 hora para datos de sesión

# Cliente Redis (lazy initialization)
_redis_client = None


def get_redis_client():
    """Obtiene el cliente Redis (singleton con lazy init)."""
    global _redis_client
    
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(**REDIS_CONFIG)
            # Verificar conexión
            _redis_client.ping()
            logger.info(f"Conexión Redis establecida: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
        except ImportError:
            logger.warning("Módulo redis no instalado. Cache deshabilitado.")
            return None
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}. Cache deshabilitado.")
            return None
    
    return _redis_client


def _make_key(prefix: str, *args, **kwargs) -> str:
    """Genera una clave única para el cache basada en los argumentos."""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
    return f"integra:{prefix}:{key_hash}"


# =====================================================
# FUNCIONES BÁSICAS DE CACHE
# =====================================================

def cache_get(key: str) -> Optional[Any]:
    """Obtiene un valor del cache."""
    client = get_redis_client()
    if client is None:
        return None
    
    try:
        value = client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Error al leer cache: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """Guarda un valor en el cache con TTL."""
    client = get_redis_client()
    if client is None:
        return False
    
    try:
        serialized = json.dumps(value, default=str)
        client.setex(key, ttl, serialized)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Error al escribir cache: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Elimina una clave del cache."""
    client = get_redis_client()
    if client is None:
        return False
    
    try:
        client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logger.warning(f"Error al eliminar cache: {e}")
        return False


def cache_invalidate_pattern(pattern: str) -> int:
    """Invalida todas las claves que coinciden con un patrón."""
    client = get_redis_client()
    if client is None:
        return 0
    
    try:
        keys = client.keys(f"integra:{pattern}:*")
        if keys:
            deleted = client.delete(*keys)
            logger.info(f"Cache INVALIDATE: {deleted} claves con patrón '{pattern}'")
            return deleted
        return 0
    except Exception as e:
        logger.warning(f"Error al invalidar cache: {e}")
        return 0


# =====================================================
# DECORADOR PARA CACHEAR FUNCIONES
# =====================================================

def cached(prefix: str, ttl: int = DEFAULT_TTL):
    """
    Decorador para cachear el resultado de una función.
    
    Args:
        prefix: Prefijo para la clave de cache
        ttl: Tiempo de vida en segundos
        
    Example:
        @cached('ranking', ttl=600)
        def get_ranking_semanal(semana, anio):
            # ... query pesado ...
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave única
            cache_key = _make_key(prefix, *args, **kwargs)
            
            # Intentar obtener del cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            
            if result is not None:
                cache_set(cache_key, result, ttl)
            
            return result
        
        # Agregar método para invalidar este cache específico
        wrapper.invalidate = lambda: cache_invalidate_pattern(prefix)
        
        return wrapper
    return decorator


# =====================================================
# FUNCIONES DE CACHE ESPECÍFICAS
# =====================================================

def cache_ranking(semana: int, anio: int, data: Any, ttl: int = QUERY_TTL):
    """Cachea datos de ranking semanal."""
    key = f"integra:ranking:{anio}:{semana}"
    return cache_set(key, data, ttl)


def get_cached_ranking(semana: int, anio: int) -> Optional[Any]:
    """Obtiene ranking cacheado."""
    key = f"integra:ranking:{anio}:{semana}"
    return cache_get(key)


def invalidate_ranking_cache():
    """Invalida todo el cache de rankings."""
    return cache_invalidate_pattern('ranking')


def cache_user_session(user_id: int, data: Any, ttl: int = SESSION_TTL):
    """Cachea datos de sesión de usuario."""
    key = f"integra:session:{user_id}"
    return cache_set(key, data, ttl)


def get_cached_user_session(user_id: int) -> Optional[Any]:
    """Obtiene datos de sesión cacheados."""
    key = f"integra:session:{user_id}"
    return cache_get(key)


# =====================================================
# UTILIDADES
# =====================================================

def get_cache_stats() -> dict:
    """Obtiene estadísticas del cache."""
    client = get_redis_client()
    if client is None:
        return {'status': 'disabled'}
    
    try:
        info = client.info('memory')
        return {
            'status': 'connected',
            'used_memory': info.get('used_memory_human', 'N/A'),
            'peak_memory': info.get('used_memory_peak_human', 'N/A'),
            'keys': client.dbsize(),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def flush_all_cache():
    """Elimina todo el cache (usar con precaución)."""
    client = get_redis_client()
    if client is None:
        return False
    
    try:
        # Solo eliminar claves de integra, no todo Redis
        keys = client.keys('integra:*')
        if keys:
            client.delete(*keys)
            logger.info(f"Cache FLUSH: {len(keys)} claves eliminadas")
        return True
    except Exception as e:
        logger.error(f"Error al limpiar cache: {e}")
        return False
