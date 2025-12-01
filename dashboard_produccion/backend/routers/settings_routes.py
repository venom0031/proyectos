"""
Rutas para configuración del sistema
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import json
from pathlib import Path

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    responses={404: {"description": "Not found"}},
)

# Archivo de configuración
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"


class OdooConfig(BaseModel):
    """Modelo de configuración de Odoo"""
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str


class TestConnectionRequest(BaseModel):
    """Request para probar conexión"""
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str


def load_config() -> dict:
    """Carga configuración desde archivo o variables de entorno"""
    config = {
        "odoo_url": os.getenv("ODOO_URL", ""),
        "odoo_db": os.getenv("ODOO_DB", ""),
        "odoo_user": os.getenv("ODOO_USER", ""),
        "odoo_password": "",  # No devolver password por seguridad
        "has_password": bool(os.getenv("ODOO_PASSWORD", ""))
    }
    
    # Si existe archivo de config, usarlo
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                file_config = json.load(f)
                config["odoo_url"] = file_config.get("odoo_url", config["odoo_url"])
                config["odoo_db"] = file_config.get("odoo_db", config["odoo_db"])
                config["odoo_user"] = file_config.get("odoo_user", config["odoo_user"])
                config["has_password"] = bool(file_config.get("odoo_password", ""))
        except:
            pass
    
    return config


def save_config(config: dict) -> bool:
    """Guarda configuración en archivo"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


@router.get("/odoo")
async def get_odoo_config():
    """Obtiene la configuración actual de Odoo (sin password)"""
    return load_config()


@router.post("/odoo")
async def save_odoo_config(config: OdooConfig):
    """Guarda la configuración de Odoo"""
    config_dict = {
        "odoo_url": config.odoo_url,
        "odoo_db": config.odoo_db,
        "odoo_user": config.odoo_user,
        "odoo_password": config.odoo_password
    }
    
    if save_config(config_dict):
        # Actualizar variables de entorno en memoria
        os.environ["ODOO_URL"] = config.odoo_url
        os.environ["ODOO_DB"] = config.odoo_db
        os.environ["ODOO_USER"] = config.odoo_user
        os.environ["ODOO_PASSWORD"] = config.odoo_password
        
        # Recargar conexión Odoo
        try:
            from backend.core.odoo_connection import odoo
            odoo.url = config.odoo_url
            odoo.db = config.odoo_db
            odoo.username = config.odoo_user
            odoo.password = config.odoo_password
            odoo.uid = None  # Forzar reconexión
        except:
            pass
        
        return {"success": True, "message": "Configuración guardada correctamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al guardar configuración")


@router.post("/test-connection")
async def test_odoo_connection(request: TestConnectionRequest):
    """Prueba la conexión a Odoo con las credenciales proporcionadas"""
    import xmlrpc.client
    
    try:
        # Probar conexión
        url = request.odoo_url.rstrip("/")
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        
        # Obtener versión (no requiere auth)
        version = common.version()
        
        # Intentar autenticación
        uid = common.authenticate(
            request.odoo_db,
            request.odoo_user,
            request.odoo_password,
            {}
        )
        
        if uid:
            return {
                "success": True,
                "message": f"Conexión exitosa. Usuario ID: {uid}",
                "version": version.get("server_version", "Unknown"),
                "uid": uid
            }
        else:
            return {
                "success": False,
                "message": "Credenciales inválidas. Verifica usuario y contraseña."
            }
            
    except xmlrpc.client.Fault as e:
        return {
            "success": False,
            "message": f"Error de Odoo: {e.faultString}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error de conexión: {str(e)}"
        }


@router.get("/status")
async def get_connection_status():
    """Obtiene el estado actual de la conexión"""
    try:
        from backend.core.odoo_connection import odoo
        uid, _ = odoo.connect()
        
        if uid:
            return {
                "connected": True,
                "uid": uid,
                "url": odoo.url,
                "db": odoo.db,
                "user": odoo.username
            }
        else:
            return {"connected": False, "message": "No autenticado"}
    except Exception as e:
        return {"connected": False, "message": str(e)}
