"""
Cliente API para comunicación con el backend
"""
import requests
import streamlit as st
from typing import List, Dict, Optional
from frontend.config.settings import API_URL


class APIClient:
    """Cliente para interactuar con la API del backend"""
    
    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip("/")
    
    @st.cache_data(ttl=300)
    def search_ofs(_self, start_date: str, end_date: str) -> List[Dict]:
        """
        Busca órdenes de fabricación por rango de fechas
        
        Args:
            start_date: Fecha de inicio (YYYY-MM-DD)
            end_date: Fecha de fin (YYYY-MM-DD)
        
        Returns:
            Lista de órdenes de fabricación
        """
        try:
            response = requests.get(
                f"{_self.base_url}/of/search",
                params={"start_date": start_date, "end_date": end_date},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error al buscar órdenes: {e}")
            return []
    
    @st.cache_data(ttl=300)
    def get_of_data(_self, of_id: int) -> Optional[Dict]:
        """
        Obtiene el detalle completo de una orden de fabricación
        
        Args:
            of_id: ID de la orden de fabricación
        
        Returns:
            Datos completos de la OF o None si hay error
        """
        try:
            response = requests.get(
                f"{_self.base_url}/of/{of_id}",
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error al obtener datos de OF: {e}")
            return None


# Instancia global del cliente
api_client = APIClient()
