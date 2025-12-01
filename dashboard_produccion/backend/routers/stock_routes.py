"""
Rutas para el Dashboard de Stock
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from backend.services.stock_service import stock_service
from backend.core.auth import require_user

router = APIRouter(
    prefix="/stock",
    tags=["stock"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_user)]
)

@router.get("/dashboard")
async def get_stock_dashboard():
    """
    Obtiene datos agregados para el gráfico de stock de cámaras.
    Incluye capacidad y posiciones ocupadas.
    """
    try:
        return stock_service.get_chambers_stock()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pallets")
async def get_pallets(
    location_id: int = Query(..., description="ID de la ubicación/cámara"),
    category: Optional[str] = Query(None, description="Filtro por Especie - Condición")
):
    """
    Obtiene lista de pallets detallada.
    """
    try:
        return stock_service.get_pallets(location_id, category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lots")
async def get_lots_by_category(
    category: str = Query(..., description="Categoría en formato 'Especie - Condición'"),
    location_ids: Optional[str] = Query(None, description="IDs de ubicaciones separados por coma")
):
    """
    Obtiene lotes agrupados por categoría con información de antigüedad.
    """
    try:
        loc_ids = None
        if location_ids:
            loc_ids = [int(x.strip()) for x in location_ids.split(",") if x.strip()]
        
        return stock_service.get_lots_by_category(category, loc_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
