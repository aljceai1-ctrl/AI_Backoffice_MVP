"""Tests for analytics endpoints."""
from tests.conftest import auth_headers


def test_overview(client, admin_user, db, tenant):
    from app.models.invoice import Invoice
    db.add(Invoice(tenant_id=tenant.id, vendor="V", status="NEW"))
    db.add(Invoice(tenant_id=tenant.id, vendor="V", status="APPROVED"))
    db.flush()

    resp = client.get("/api/analytics/overview", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_invoices"] == 2
    assert "by_status" in data


def test_payment_analytics(client, admin_user):
    resp = client.get("/api/analytics/payments", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert "over_time" in data
    assert "top_vendors" in data


def test_effectiveness(client, admin_user):
    resp = client.get("/api/analytics/effectiveness", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert "mean_time_to_approval_hours" in data
    assert "top_exception_codes" in data


def test_ingestion(client, admin_user):
    resp = client.get("/api/analytics/ingestion", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert "daily" in data
    assert "overall_failure_rate" in data


def test_audit_effectiveness(client, admin_user):
    resp = client.get("/api/analytics/audit-effectiveness", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert "rejection_rate" in data
