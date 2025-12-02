"""
Configuracion centralizada de la aplicacion
"""
from typing import Optional, List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al .env (raiz del proyecto)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Configuracion de la aplicacion"""

    # Odoo Configuration
    ODOO_URL: str
    ODOO_DB: str
    ODOO_USER: str
    ODOO_PASSWORD: str
    SETTINGS_TOKEN: Optional[str] = None

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
