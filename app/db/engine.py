"""SQLAlchemy engine factory."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.core.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy Engine using DATABASE_URL from settings."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
