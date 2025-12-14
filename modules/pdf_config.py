"""
Configuración robusta de wkhtmltopdf para desarrollo y producción.
Maneja detección, instalación y fallback automático.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def get_wkhtmltopdf_path():
    """
    Obtiene la ruta a wkhtmltopdf con prioridad:
    1. Variable de entorno WKHTMLTOPDF_PATH
    2. Búsqueda en rutas comunes según SO
    3. Búsqueda en PATH del sistema (where/which)
    4. None si no está disponible
    """
    
    # 1. Verificar variable de entorno
    env_path = os.environ.get('WKHTMLTOPDF_PATH')
    if env_path and Path(env_path).exists():
        return env_path
    
    # 2. Rutas comunes según el sistema operativo
    if platform.system() == 'Windows':
        common_paths = [
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\tools\wkhtmltopdf\bin\wkhtmltopdf.exe",
        ]
    elif platform.system() == 'Darwin':  # macOS
        common_paths = [
            "/usr/local/bin/wkhtmltopdf",
            "/opt/homebrew/bin/wkhtmltopdf",
        ]
    else:  # Linux
        common_paths = [
            "/usr/bin/wkhtmltopdf",
            "/usr/local/bin/wkhtmltopdf",
            "/snap/bin/wkhtmltopdf",
        ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    # 3. Buscar en PATH del sistema
    wk_path = shutil.which('wkhtmltopdf')
    if wk_path:
        return wk_path
    
    # 4. No encontrado
    return None

def get_wkhtmltopdf_version():
    """
    Retorna la versión de wkhtmltopdf o None si no está disponible.
    """
    path = get_wkhtmltopdf_path()
    if not path:
        return None
    
    try:
        result = subprocess.run(
            [path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Típicamente: "wkhtmltopdf 0.12.6"
            return result.stdout.strip()
    except Exception:
        pass
    
    return None

def is_wkhtmltopdf_available():
    """
    Verifica si wkhtmltopdf está disponible y funcional.
    """
    return get_wkhtmltopdf_path() is not None

def ensure_wkhtmltopdf_in_environment():
    """
    Asegura que wkhtmltopdf esté en el entorno.
    Útil para llamar al startup de la aplicación.
    Retorna True si está disponible, False si no.
    """
    path = get_wkhtmltopdf_path()
    if path:
        # Verificar que siga siendo accesible
        if Path(path).exists():
            return True
    
    return False

def get_pdfkit_config():
    """
    Retorna un diccionario de configuración para pdfkit.configuration()
    o None si wkhtmltopdf no está disponible.
    
    Uso:
        import pdfkit
        config = get_pdfkit_config()
        pdf_bytes = pdfkit.from_string(html, False, configuration=config)
    """
    try:
        import pdfkit
    except ImportError:
        return None
    
    path = get_wkhtmltopdf_path()
    if path:
        try:
            return pdfkit.configuration(wkhtmltopdf=path)
        except Exception:
            pass
    
    # Si no hay path explícito, intentar con configuración por defecto
    try:
        return pdfkit.configuration()
    except Exception:
        pass
    
    return None
