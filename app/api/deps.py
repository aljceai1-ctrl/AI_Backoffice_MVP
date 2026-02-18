"""Shared FastAPI dependencies used across routers."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import require_api_key
from app.db.session import get_db


def get_request_id(request: Request) -> str:
    """Extract the request-scoped UUID injected by RequestIDMiddleware."""
    return getattr(request.state, "request_id", "unknown")


# Re-export dependency callables for clean import in routers
__all__ = ["get_db", "require_api_key", "get_request_id"]
