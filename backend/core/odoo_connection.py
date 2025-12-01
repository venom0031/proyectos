"""
Módulo de conexión a Odoo
"""
import xmlrpc.client
from typing import Tuple
from backend.config.settings import settings


class OdooConnection:
    """Gestiona la conexión con Odoo"""
    
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.user = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self._uid = None
        self._models = None
    
    def connect(self) -> Tuple:
        """
        Establece conexión con Odoo y retorna uid y models
        
        Returns:
            Tuple: (uid, models)
        
        Raises:
            Exception: Si la autenticación falla
        """
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            uid = common.authenticate(self.db, self.user, self.password, {})
            
            if not uid:
                raise Exception("Authentication failed")
            
            models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            
            self._uid = uid
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
        if not self._uid or not self._models:
            self.connect()
        
        kwargs = kwargs or {}
        
        return self._models.execute_kw(
            self.db, self._uid, self.password,
            model, method, args, kwargs
        )


# Instancia global de conexión
odoo = OdooConnection()
