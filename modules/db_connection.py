# ============================================
# MÓDULO DE CONEXIÓN A POSTGRESQL
# Maneja pool de conexiones y contexto RLS
# ============================================
import psycopg2
from psycopg2 import pool, extras
from typing import Optional, Dict, Any, List
import logging
from contextlib import contextmanager

from config import DB_CONFIG, POOL_CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pool de conexiones global
connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_pool():
    """Inicializa el pool de conexiones a PostgreSQL"""
    global connection_pool
    
    if connection_pool is None:
        try:
            # UTF8 funciona ahora que la password es correcta
            db_config = DB_CONFIG.copy()
            db_config['options'] = '-c client_encoding=UTF8'
            
            connection_pool = pool.ThreadedConnectionPool(
                POOL_CONFIG['minconn'],
                POOL_CONFIG['maxconn'],
                **db_config
            )
            logger.info(f"Pool de conexiones creado: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        except Exception as e:
            logger.error(f"Error al crear pool de conexiones: {e}")
            raise


def close_pool():
    """Cierra el pool de conexiones"""
    global connection_pool
    
    if connection_pool is not None:
        connection_pool.closeall()
        connection_pool = None
        logger.info("Pool de conexiones cerrado")


@contextmanager
def get_connection(user_id: Optional[int] = None, is_admin: bool = False):
    """
    Context manager para obtener una conexión del pool.
    Automáticamente establece el contexto de usuario para RLS.
    
    Args:
        user_id: ID del usuario autenticado (para RLS)
        is_admin: Si el usuario es administrador (bypass RLS)
        
    Yields:
        connection: Conexión psycopg2
        
    Example:
        with get_connection(user_id=1) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM datos_diarios")
            ...
    """
    if connection_pool is None:
        init_pool()
    
    conn = None
    try:
        conn = connection_pool.getconn()
        
        # Establecer contexto de usuario para RLS
        if user_id is not None:
            set_user_context(conn, user_id, is_admin)
        
        yield conn
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en conexión: {e}")
        raise
    finally:
        if conn:
            connection_pool.putconn(conn)


def set_user_context(conn, user_id: int, is_admin: bool = False):
    """
    Establece el contexto de usuario en la conexión para aplicar RLS.
    
    Args:
        conn: Conexión psycopg2
        user_id: ID del usuario
        is_admin: Si el usuario es administrador
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT set_user_context(%s, %s)", (user_id, is_admin))
            conn.commit()
            logger.debug(f"Contexto RLS establecido: user_id={user_id}, is_admin={is_admin}")
    except Exception as e:
        logger.error(f"Error al establecer contexto RLS: {e}")
        raise


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    fetch_one: bool = False,
    fetch_all: bool = True,
    return_dict: bool = True
) -> Optional[Any]:
    """
    Ejecuta un query SELECT con contexto RLS aplicado.
    
    Args:
        query: SQL query
        params: Parámetros para el query
        user_id: ID del usuario (para RLS)
        is_admin: Si es administrador
        fetch_one: Si solo se debe retornar un registro
        fetch_all: Si se deben retornar todos los registros
        return_dict: Si se debe retornar como dict (True) o tupla (False)
        
    Returns:
        Resultados del query (list of dict, dict, o None)
    """
    with get_connection(user_id, is_admin) as conn:
        cursor_factory = extras.RealDictCursor if return_dict else None
        
        with conn.cursor(cursor_factory=cursor_factory) as cursor:
            cursor.execute(query, params or ())
            
            # Si es un INSERT...RETURNING, necesitamos commit
            if 'RETURNING' in query.upper():
                conn.commit()
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return None


def execute_update(
    query: str,
    params: Optional[tuple] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False
) -> int:
    """
    Ejecuta un query INSERT/UPDATE/DELETE.
    
    Args:
        query: SQL query
        params: Parámetros para el query
        user_id: ID del usuario (para RLS)
        is_admin: Si es administrador
        
    Returns:
        Número de filas afectadas
    """
    with get_connection(user_id, is_admin) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos.
    
    Returns:
        True si la conexión es exitosa, False en caso contrario
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()
                logger.info(f"Conexión exitosa: {version[0]}")
                return True
    except Exception as e:
        logger.error(f"Error al conectar: {e}")
        return False


def get_table_count(table_name: str) -> int:
    """
    Obtiene el número de registros en una tabla.
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        Número de registros
    """
    query = f"SELECT COUNT(*) as count FROM {table_name}"
    result = execute_query(query, fetch_one=True, return_dict=True)
    return result['count'] if result else 0


# Inicializar pool al importar el módulo
# DISABLED - se inicializa lazy cuando se necesita
# try:
#     init_pool()
# except Exception as e:
#     logger.warning(f"No se pudo inicializar el pool al importar: {e}")
