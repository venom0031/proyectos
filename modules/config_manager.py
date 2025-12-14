"""
Módulo de gestión de configuración de la aplicación.
Permite al admin configurar filtros por defecto y notas semanales.
"""
import json
from typing import Optional, List
from db_connection import execute_query, execute_update


def get_config(clave: str) -> Optional[str]:
    """Obtiene el valor de una configuración por clave."""
    result = execute_query(
        "SELECT valor FROM configuracion_app WHERE clave = %s",
        (clave,),
        fetch_one=True
    )
    return result['valor'] if result else None


def set_config(clave: str, valor: str, user_id: int = None) -> bool:
    """Guarda o actualiza una configuración."""
    try:
        execute_update(
            """
            INSERT INTO configuracion_app (clave, valor, updated_by, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (clave) DO UPDATE SET
                valor = EXCLUDED.valor,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (clave, valor, user_id)
        )
        return True
    except Exception as e:
        print(f"Error guardando config: {e}")
        return False


def get_filtros_defecto() -> List[str]:
    """Obtiene la lista de establecimientos por defecto para filtros."""
    valor = get_config('filtros_defecto')
    if valor:
        try:
            return json.loads(valor)
        except json.JSONDecodeError:
            return []
    return []


def set_filtros_defecto(establecimientos: List[str], user_id: int = None) -> bool:
    """Guarda la lista de establecimientos por defecto."""
    return set_config('filtros_defecto', json.dumps(establecimientos), user_id)


def get_nota_semanal() -> Optional[str]:
    """Obtiene la nota semanal actual."""
    return get_config('nota_semanal')


def set_nota_semanal(nota: str, user_id: int = None) -> bool:
    """Guarda la nota semanal."""
    return set_config('nota_semanal', nota, user_id)


def is_nota_visible() -> bool:
    """Verifica si la nota semanal debe mostrarse."""
    valor = get_config('nota_semanal_visible')
    return valor.lower() == 'true' if valor else True


def set_nota_visible(visible: bool, user_id: int = None) -> bool:
    """Establece si la nota semanal debe mostrarse."""
    return set_config('nota_semanal_visible', 'true' if visible else 'false', user_id)


def get_orden_defecto() -> dict:
    """Obtiene la configuración de ordenamiento por defecto de la matriz."""
    valor = get_config('orden_matriz_defecto')
    if valor:
        try:
            return json.loads(valor)
        except json.JSONDecodeError:
            return {'columna': 'Establecimiento', 'ascendente': True}
    return {'columna': 'Establecimiento', 'ascendente': True}


def set_orden_defecto(columna: str, ascendente: bool, user_id: int = None) -> bool:
    """Guarda la configuración de ordenamiento por defecto."""
    return set_config('orden_matriz_defecto', json.dumps({
        'columna': columna,
        'ascendente': ascendente
    }), user_id)
