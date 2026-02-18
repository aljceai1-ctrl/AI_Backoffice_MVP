"""Pytest fixtures — isolated Postgres test database per test session."""

import io
import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ─── Test DB URL ──────────────────────────────────────────────────────────────

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://backoffice:backoffice@localhost:5433/backoffice_test",
)

# ─── API key used in tests ────────────────────────────────────────────────────

API_KEY = "dev-api-key-change-me"


# ─── Session-scoped engine: create all tables once ───────────────────────────


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


# ─── Function-scoped: fresh session + table truncation per test ───────────────


@pytest.fixture(autouse=True)
def clean_tables(engine):
    """Truncate all tables before each test for isolation."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE audit_events, approvals, invoice_exceptions, invoices"
                " RESTART IDENTITY CASCADE"
            )
        )
        conn.commit()
    yield


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ─── TestClient with overridden DB dependency ─────────────────────────────────


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture
def auth_headers() -> dict:
    return {"X-API-Key": API_KEY}


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Override UPLOAD_DIR to a temporary directory for each test."""
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    # Bust lru_cache so the new env var is picked up
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def make_fake_file(content: bytes = b"fake invoice content", filename: str = "invoice.pdf"):
    """Return a multipart-compatible tuple for file upload tests."""
    return ("file", (filename, io.BytesIO(content), "application/pdf"))
