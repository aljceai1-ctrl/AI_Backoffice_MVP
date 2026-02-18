"""API key authentication dependency."""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.settings import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Depends(_api_key_header)) -> str:
    """Validate the X-API-Key header against the configured secret.

    Raises 401 if the key is absent or incorrect.
    Returns the key string on success (for logging / audit use).
    """
    settings = get_settings()
    if not api_key or api_key != settings.BACKOFFICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
    return api_key
