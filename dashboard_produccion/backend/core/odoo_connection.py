"""
Módulo de conexión a Odoo
Soporta configuración desde .env y desde config.json (interfaz web)
"""
import xmlrpc.client
import os
import json
from pathlib import Path
from typing import Tuple


def load_odoo_config():
    """Carga configuración de Odoo desde config.json o variables de entorno"""
    config_file = Path(__file__).parent.parent.parent / "config.json"
    
    # Valores por defecto desde variables de entorno
    config = {
        "url": os.getenv("ODOO_URL", ""),
        "db": os.getenv("ODOO_DB", ""),
        "user": os.getenv("ODOO_USER", ""),
        "password": os.getenv("ODOO_PASSWORD", "")
    }
    
    # Si existe config.json, sobrescribir con esos valores
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                if file_config.get("odoo_url"):
                    config["url"] = file_config["odoo_url"]
                if file_config.get("odoo_db"):
                    config["db"] = file_config["odoo_db"]
                if file_config.get("odoo_user"):
                    config["user"] = file_config["odoo_user"]
                if file_config.get("odoo_password"):
                    config["password"] = file_config["odoo_password"]
        except Exception as e:
            print(f"Error loading config.json: {e}")
    
    return config


class OdooConnection:
    """Gestiona la conexión con Odoo"""
    
    def __init__(self):
        config = load_odoo_config()
        self.url = config["url"]
        self.db = config["db"]
        self.username = config["user"]
        self.password = config["password"]
        self.uid = None
        self._models = None
    
    def reload_config(self):
        """Recarga la configuración desde archivo"""
        config = load_odoo_config()
        self.url = config["url"]
        self.db = config["db"]
        self.username = config["user"]
        self.password = config["password"]
        self.uid = None
        self._models = None
    
    def connect(self) -> Tuple:
        """
        Establece conexión con Odoo y retorna uid y models
        
        Returns:
            Tuple: (uid, models)
        
        Raises:
            Exception: Si la autenticación falla
        """
        # Recargar config si no hay credenciales
        if not self.url or not self.password:
            self.reload_config()
        
        try:
            url = self.url.rstrip("/")
            common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(self.db, self.username, self.password, {})
            
            if not uid:
                raise Exception("Authentication failed - check credentials")
            
            models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
            
            self.uid = uid
            self._models = models
            
            return uid, models
            
        except Exception as e:
            print(f"Error connecting to Odoo: {e}")
            raise
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: dict = None):
        """
        Ejecuta un método en un modelo de Odoo
        
        Args:
            model: Nombre del modelo de Odoo
            method: Método a ejecutar
            args: Argumentos posicionales
            kwargs: Argumentos con nombre
        
        Returns:
            Resultado de la llamada
        """
        if not self.uid or not self._models:
            self.connect()
        
        kwargs = kwargs or {}
        
        return self._models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )


# Instancia global de conexión
odoo = OdooConnection()
