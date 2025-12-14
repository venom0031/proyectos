"""Script para insertar configuración inicial"""
import sys
sys.path.insert(0, 'modules')
from db_connection import execute_update

# Insertar configuración inicial
configs = [
    ('filtros_defecto', '[]'),
    ('nota_semanal', ''),
    ('nota_semanal_visible', 'true')
]

for clave, valor in configs:
    try:
        execute_update(
            "INSERT INTO configuracion_app (clave, valor) VALUES (%s, %s) ON CONFLICT (clave) DO NOTHING",
            (clave, valor)
        )
        print(f"  OK: {clave}")
    except Exception as e:
        print(f"  Error {clave}: {e}")

print("Configuración inicial insertada")
