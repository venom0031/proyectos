"""
Dashboard de Producción Odoo - Backend API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.routers import of_routes, stock_routes, sales_routes, settings_routes

# Crear aplicación
app = FastAPI(
    title="Odoo Production Dashboard API",
    description="API para visualización de datos de producción de Odoo",
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
    """Endpoint raíz de la API"""
    return {
        "message": "Odoo Production Dashboard API",
        "version": "2.0.0",
        "docs": "/docs"
    }


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