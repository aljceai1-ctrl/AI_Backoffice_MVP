"""Pytest fixtures for backend tests."""
import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://backoffice:backoffice@localhost:5432/backoffice_test")

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

TEST_DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        # Clean all tables
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f"DELETE FROM {table.name}"))
        session.commit()
        session.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def tenant(db: Session) -> Tenant:
    t = Tenant(name="Test Corp", inbound_email_alias="testcorp")
    db.add(t)
    db.flush()
    return t


@pytest.fixture()
def tenant2(db: Session) -> Tenant:
    t = Tenant(name="Other Corp", inbound_email_alias="othercorp")
    db.add(t)
    db.flush()
    return t


@pytest.fixture()
def admin_user(db: Session, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id, email="admin@test.local",
        password_hash=hash_password("testpass"), full_name="Admin", role="ADMIN",
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture()
def viewer_user(db: Session, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id, email="viewer@test.local",
        password_hash=hash_password("testpass"), full_name="Viewer", role="VIEWER",
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture()
def approver_user(db: Session, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id, email="approver@test.local",
        password_hash=hash_password("testpass"), full_name="Approver", role="APPROVER",
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture()
def other_tenant_user(db: Session, tenant2: Tenant) -> User:
    u = User(
        tenant_id=tenant2.id, email="other@other.local",
        password_hash=hash_password("testpass"), full_name="Other Admin", role="ADMIN",
    )
    db.add(u)
    db.flush()
    return u


def auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}
