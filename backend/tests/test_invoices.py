"""Tests for invoice endpoints."""
import io

from tests.conftest import auth_headers


def test_upload_invoice(client, admin_user):
    file = io.BytesIO(b"fake pdf content")
    resp = client.post(
        "/api/invoices/upload",
        files={"file": ("test.pdf", file, "application/pdf")},
        data={"vendor": "Test Vendor", "invoice_number": "INV-001", "amount": "5000", "currency": "AED", "invoice_date": "2025-01-15"},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor"] == "Test Vendor"
    assert data["status"] in ("APPROVAL_PENDING", "VALIDATED")


def test_list_invoices(client, admin_user, db, tenant):
    from app.models.invoice import Invoice
    for i in range(3):
        db.add(Invoice(tenant_id=tenant.id, vendor=f"V{i}", status="NEW"))
    db.flush()

    resp = client.get("/api/invoices", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


def test_mark_paid(client, approver_user, db, tenant):
    from app.models.invoice import Invoice
    inv = Invoice(tenant_id=tenant.id, vendor="V", amount=1000, currency="AED", status="APPROVED")
    db.add(inv)
    db.flush()

    resp = client.post(f"/api/invoices/{inv.id}/mark-paid", headers=auth_headers(approver_user))
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAID"
    assert len(resp.json()["payments"]) == 1
