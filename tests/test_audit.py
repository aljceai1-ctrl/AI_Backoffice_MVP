"""Tests for the /audit endpoint."""

from datetime import date, timedelta


def test_audit_returns_events(client, auth_headers, upload_dir):
    """Uploading an invoice must produce at least one audit event."""
    from tests.conftest import make_fake_file

    client.post(
        "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
    )
    resp = client.get("/audit", headers=auth_headers)
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert all("event_type" in e for e in events)


def test_audit_filter_by_entity_id(client, auth_headers, upload_dir):
    from tests.conftest import make_fake_file

    up = client.post(
        "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
    )
    invoice_id = up.json()["id"]

    resp = client.get(f"/audit?entity_id={invoice_id}", headers=auth_headers)
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert all(e["entity_id"] == invoice_id for e in events)


def test_audit_date_filter(client, auth_headers, upload_dir):
    from tests.conftest import make_fake_file

    client.post(
        "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
    )
    today = date.today().isoformat()
    resp = client.get(f"/audit?from={today}&to={today}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_audit_requires_auth(client):
    resp = client.get("/audit")
    assert resp.status_code == 401


def test_audit_limit_param(client, auth_headers, upload_dir):
    from tests.conftest import make_fake_file

    # Create several events
    for _ in range(5):
        client.post(
            "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
        )

    resp = client.get("/audit?limit=3", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 3
