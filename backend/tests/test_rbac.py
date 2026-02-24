"""Tests for RBAC: verify role restrictions on endpoints."""
from tests.conftest import auth_headers


def test_viewer_cannot_create_user(client, viewer_user):
    resp = client.post("/api/users", json={"email": "new@test.local", "password": "pass123", "role": "VIEWER"},
                       headers=auth_headers(viewer_user))
    assert resp.status_code == 403


def test_admin_can_create_user(client, admin_user):
    resp = client.post("/api/users", json={"email": "new@test.local", "password": "pass123", "role": "UPLOADER"},
                       headers=auth_headers(admin_user))
    assert resp.status_code == 201
    assert resp.json()["role"] == "UPLOADER"


def test_viewer_cannot_approve(client, viewer_user, db, tenant):
    from app.models.invoice import Invoice
    inv = Invoice(tenant_id=tenant.id, vendor="Test", status="APPROVAL_PENDING")
    db.add(inv)
    db.flush()
    resp = client.post(f"/api/invoices/{inv.id}/approve", headers=auth_headers(viewer_user))
    assert resp.status_code == 403


def test_approver_can_approve(client, approver_user, db, tenant):
    from app.models.invoice import Invoice
    inv = Invoice(tenant_id=tenant.id, vendor="Test", invoice_number="INV-001",
                  amount=1000, currency="AED", status="APPROVAL_PENDING")
    db.add(inv)
    db.flush()
    resp = client.post(f"/api/invoices/{inv.id}/approve", headers=auth_headers(approver_user))
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"
