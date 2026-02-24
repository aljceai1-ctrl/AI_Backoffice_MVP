"""Tests for auth endpoints."""
from tests.conftest import auth_headers


def test_login_success(client, admin_user):
    resp = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    resp = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "wrong"})
    assert resp.status_code == 401


def test_login_nonexistent(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@test.local", "password": "pass"})
    assert resp.status_code == 401


def test_me(client, admin_user):
    resp = client.get("/api/auth/me", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.local"
    assert data["role"] == "ADMIN"


def test_me_unauthorized(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
