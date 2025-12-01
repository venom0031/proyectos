"""
Funciones auxiliares para limpieza y procesamiento de datos
"""


def clean(value):
    """
    Limpia valores de Odoo convirtiendo listas [id, name] a diccionarios
    
    Args:
        value: Valor a limpiar
    
    Returns:
        Diccionario con id y name si es una lista de 2 elementos, sino el valor original
    """
    if isinstance(value, list) and len(value) == 2:
        return {"id": value[0], "name": value[1]}
    return value


def clean_record(rec: dict) -> dict:
    """
    Limpia todos los campos de un registro de Odoo
    
    Args:
        rec: Diccionario con datos de Odoo
    
    Returns:
        Diccionario limpio
    """
    return {k: clean(v) for k, v in rec.items()}


def get_name(val):
    """
    Extrae el nombre de un valor que puede ser dict o False
    
    Args:
        val: Valor a procesar
    
    Returns:
        Nombre si es un dict, "N/A" en caso contrario
    """
    if isinstance(val, dict):
        return val.get("name", "N/A")
    return "N/A"
