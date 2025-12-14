import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'modules'))
from db_connection import execute_update, execute_query

"""Script para limpiar datos operativos y dejar solo usuarios/empresas.
Ejecuta truncates sobre tablas de carga y ajusta password del usuario admin a 'admin'.
Uso:
    cd c:\\new\\INTEGRA\\streamlit_app
    python scripts\\clean_db.py
"""

TABLES_TO_TRUNCATE = [
    'datos_diarios',
    'datos_semanales',
    'historico_mdat'
]

LOG_TABLE = 'upload_logs'

def truncate_tables():
    print("--- Truncando tablas de datos ---")
    for tbl in TABLES_TO_TRUNCATE:
        try:
            execute_update(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE")
            print(f"OK: {tbl} truncada")
        except Exception as e:
            print(f"ERROR truncando {tbl}: {e}")
    # logs si existe
    try:
        execute_update(f"TRUNCATE TABLE {LOG_TABLE} RESTART IDENTITY CASCADE")
        print(f"OK: {LOG_TABLE} truncada")
    except Exception as e:
        if 'does not exist' in str(e) or 'no existe' in str(e):
            print("(skip) Tabla upload_logs no existe")
        else:
            print(f"ERROR truncando upload_logs: {e}")


def set_admin_password():
    print("--- Ajustando password admin ---")
    try:
        # Usar función hash_password si existe
        execute_update("UPDATE usuarios SET password_hash = hash_password(%s) WHERE username='admin'", ('admin',))
        print("OK: password de 'admin' actualizado a 'admin'")
    except Exception as e:
        print(f"ERROR actualizando password admin: {e}")


def show_counts():
    print("--- Resumen post-limpieza ---")
    for tbl in ['empresas','establecimientos','usuarios','usuario_empresa','datos_semanales','datos_diarios','historico_mdat']:
        try:
            row = execute_query(f"SELECT COUNT(*) AS c FROM {tbl}", fetch_one=True)
            print(f"{tbl}: {row['c']}")
        except Exception as e:
            print(f"{tbl}: ERROR ({e})")


def main():
    truncate_tables()
    set_admin_password()
    show_counts()
    print("\nLimpieza completada. Puedes iniciar sesión con usuario 'admin' y password 'admin'.")

if __name__ == '__main__':
    main()
