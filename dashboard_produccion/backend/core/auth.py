"""
Dependencias para validar usuarios usando su API Key de Odoo.
"""
import time
import xmlrpc.client
from typing import Optional, Dict

from fastapi import Header, HTTPException, status

from backend.config.settings import settings


AUTH_CACHE_TTL = 300  # segundos
_AUTH_CACHE: Dict[str, Dict[str, float]] = {}


def _make_cache_key(email: str, token: str) -> str:
    return f"{email.lower()}::{token}"


def _authenticate_against_odoo(email: str, token: str) -> int:
    """Intenta autenticarse en Odoo usando API Key del usuario."""
    try:
        url = settings.ODOO_URL.rstrip("/")
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(settings.ODOO_DB, email, token, {})
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales de Odoo invalidas"
            )
        return uid
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al validar con Odoo: {exc}"
        ) from exc


def _get_cached_uid(email: str, token: str) -> Optional[int]:
    key = _make_cache_key(email, token)
    data = _AUTH_CACHE.get(key)
    if not data:
        return None
    if data["expires"] < time.time():
        _AUTH_CACHE.pop(key, None)
        return None
    return int(data["uid"])


def _set_cache(email: str, token: str, uid: int) -> None:
    key = _make_cache_key(email, token)
    _AUTH_CACHE[key] = {"uid": uid, "expires": time.time() + AUTH_CACHE_TTL}


def require_user(
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token")
):
    """Valida los headers contra Odoo (email + API Key)."""
    if not x_user_email or not x_user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Headers de autenticacion requeridos"
        )

    cached_uid = _get_cached_uid(x_user_email, x_user_token)
    if cached_uid:
        return {"email": x_user_email.lower(), "uid": cached_uid}

    uid = _authenticate_against_odoo(x_user_email, x_user_token)
    _set_cache(x_user_email, x_user_token, uid)
    return {"email": x_user_email.lower(), "uid": uid}
