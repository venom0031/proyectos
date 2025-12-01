"""
Dashboard de Produccion Odoo - Backend API
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.routers import of_routes, stock_routes, sales_routes, settings_routes
from backend.core.auth import require_user

# Crear aplicacion
app = FastAPI(
    title="Odoo Production Dashboard API",
    description="API para visualizacion de datos de produccion de Odoo",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(of_routes.router)
app.include_router(stock_routes.router)
app.include_router(sales_routes.router)
app.include_router(settings_routes.router)


@app.get("/")
def root():
    """Endpoint raiz de la API"""
    return {
        "message": "Odoo Production Dashboard API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/auth/check")
def auth_check(user=Depends(require_user)):
    """Valida las credenciales enviadas en los headers."""
    return {"email": user["email"], "uid": user["uid"]}


@app.get("/health")
def health():
    """Endpoint de salud para monitoreo"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
