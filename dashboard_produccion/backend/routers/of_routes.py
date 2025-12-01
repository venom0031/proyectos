"""
Rutas de API para Órdenes de Fabricación
"""
from fastapi import APIRouter, Query, Depends
from typing import List
from backend.services.of_service import of_service
from backend.core.auth import require_user

router = APIRouter(
    prefix="/of",
    tags=["Órdenes de Fabricación"],
    dependencies=[Depends(require_user)]
)


@router.get("/search")
def search_manufacturing_orders(
    start_date: str = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Fecha de fin (YYYY-MM-DD)")
):
    """
    Busca órdenes de fabricación por rango de fechas
    
    - **start_date**: Fecha de inicio en formato YYYY-MM-DD
    - **end_date**: Fecha de fin en formato YYYY-MM-DD
    
    Retorna una lista de órdenes de fabricación con información básica.
    """
    return of_service.search_ofs(start_date, end_date)


@router.get("/{of_id}")
def get_manufacturing_order(of_id: int):
    """
    Obtiene el detalle completo de una orden de fabricación
    
    - **of_id**: ID de la orden de fabricación
    
    Retorna:
    - Datos de la OF
    - Componentes (materia prima)
    - Subproductos
    - Detenciones
    - Horas de consumo
    - KPIs calculados
    """
    return of_service.get_of_detail(of_id)
