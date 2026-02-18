"""Tests for the /health endpoint."""


def test_health_returns_ok(client):
    """GET /health must return 200 with status=ok and require no auth."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_no_auth_required(client):
    """Health endpoint must be accessible without an API key."""
    resp = client.get("/health", headers={})
    assert resp.status_code == 200
