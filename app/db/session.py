"""Database session factory and FastAPI dependency."""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import get_engine

_SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    session: Session = _SessionLocal(bind=get_engine())
    try:
        yield session
    finally:
        session.close()
