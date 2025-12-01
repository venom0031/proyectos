"""
Rutas para el Dashboard de Containers/Ventas
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from backend.services.sales_service import sales_service
from backend.core.auth import require_user

router = APIRouter(
    prefix="/sales",
    tags=["sales"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_user)]
)


@router.get("/containers")
async def get_containers(
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    partner_id: Optional[int] = Query(None, description="ID del cliente"),
    state: Optional[str] = Query(None, description="Estado del pedido")
):
    """
    Obtiene lista de containers/ventas con su avance de producción.
    """
    try:
        return sales_service.get_containers(
            start_date=start_date,
            end_date=end_date,
            partner_id=partner_id,
            state=state
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/summary")
async def get_containers_summary():
    """
    Obtiene resumen global de containers para KPIs.
    """
    try:
        return sales_service.get_containers_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{sale_id}")
async def get_container_detail(sale_id: int):
    """
    Obtiene detalle completo de un container/venta específico.
    """
    try:
        container = sales_service.get_container_detail(sale_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container no encontrado")
        return container
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partners")
async def get_partners():
    """
    Obtiene lista de clientes que tienen pedidos.
    """
    try:
        return sales_service.get_partners_with_orders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
