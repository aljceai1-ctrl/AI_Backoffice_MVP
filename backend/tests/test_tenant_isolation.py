"""Tests for multi-tenant isolation."""
from tests.conftest import auth_headers


def test_cannot_see_other_tenant_invoices(client, admin_user, other_tenant_user, db, tenant, tenant2):
    from app.models.invoice import Invoice

    inv1 = Invoice(tenant_id=tenant.id, vendor="My Vendor", status="NEW")
    inv2 = Invoice(tenant_id=tenant2.id, vendor="Other Vendor", status="NEW")
    db.add_all([inv1, inv2])
    db.flush()

    # Admin of tenant1 should only see tenant1 invoices
    resp = client.get("/api/invoices", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    vendors = [i["vendor"] for i in data["items"]]
    assert "My Vendor" in vendors
    assert "Other Vendor" not in vendors

    # Admin of tenant2 should only see tenant2 invoices
    resp2 = client.get("/api/invoices", headers=auth_headers(other_tenant_user))
    data2 = resp2.json()
    vendors2 = [i["vendor"] for i in data2["items"]]
    assert "Other Vendor" in vendors2
    assert "My Vendor" not in vendors2


def test_cannot_access_other_tenant_invoice_detail(client, admin_user, db, tenant2):
    from app.models.invoice import Invoice

    inv = Invoice(tenant_id=tenant2.id, vendor="Secret", status="NEW")
    db.add(inv)
    db.flush()

    resp = client.get(f"/api/invoices/{inv.id}", headers=auth_headers(admin_user))
    assert resp.status_code == 404


def test_cannot_see_other_tenant_users(client, admin_user, other_tenant_user):
    resp = client.get("/api/users", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "admin@test.local" in emails
    assert "other@other.local" not in emails
