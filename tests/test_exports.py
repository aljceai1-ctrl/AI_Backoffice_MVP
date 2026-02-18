"""Tests for payment pack CSV and weekly Markdown report endpoints."""

from datetime import date, timedelta


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _full_cycle(client, auth_headers, upload_dir, vendor="Vendor A", inv_num="INV-X"):
    """Upload → extract → validate → approve an invoice; return its id."""
    from tests.conftest import make_fake_file

    # Upload
    up = client.post(
        "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
    )
    assert up.status_code == 201
    inv_id = up.json()["id"]

    # Extract
    client.post(
        f"/invoices/{inv_id}/extract",
        headers=auth_headers,
        json={
            "vendor": vendor,
            "invoice_number": inv_num,
            "invoice_date": "2024-06-01",
            "due_date": "2024-07-01",
            "amount": "9999.00",
            "currency": "AED",
        },
    )
    # Validate
    client.post(f"/invoices/{inv_id}/validate", headers=auth_headers)

    # Approve
    client.post(
        f"/invoices/{inv_id}/approve",
        headers=auth_headers,
        json={"decision": "APPROVE", "decided_by": "Finance"},
    )
    return inv_id


# ─── Payment pack ─────────────────────────────────────────────────────────────


def test_payment_pack_includes_only_approved(client, auth_headers, upload_dir):
    _full_cycle(client, auth_headers, upload_dir)

    today = date.today()
    resp = client.get(
        f"/payment-pack.csv?from={today - timedelta(days=1)}&to={today + timedelta(days=1)}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    body = resp.text
    assert "vendor" in body  # header row
    assert "Vendor A" in body
    assert "9999" in body


def test_payment_pack_excludes_non_approved(client, auth_headers, upload_dir):
    """An invoice in NEW status must not appear in the payment pack."""
    from tests.conftest import make_fake_file

    client.post(
        "/invoices/upload", headers=auth_headers, files=[make_fake_file()]
    )
    today = date.today()
    resp = client.get(
        f"/payment-pack.csv?from={today - timedelta(days=1)}&to={today + timedelta(days=1)}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    # Only header row — no data rows
    assert len(lines) == 1


def test_payment_pack_creates_audit_event(client, auth_headers, upload_dir):
    today = date.today()
    client.get(
        f"/payment-pack.csv?from={today}&to={today}",
        headers=auth_headers,
    )
    audit = client.get("/audit", headers=auth_headers).json()
    assert any(e["event_type"] == "PAYMENT_PACK_EXPORTED" for e in audit)


def test_payment_pack_requires_auth(client, upload_dir):
    today = date.today()
    resp = client.get(f"/payment-pack.csv?from={today}&to={today}")
    assert resp.status_code == 401


# ─── Weekly pack ─────────────────────────────────────────────────────────────


def test_weekly_pack_returns_markdown(client, auth_headers, upload_dir):
    _full_cycle(client, auth_headers, upload_dir)

    # Use a wide week range guaranteed to include today
    week_start = date.today() - timedelta(days=date.today().weekday() + 7)
    resp = client.get(
        f"/weekly-pack.md?week_start={week_start}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.text
    assert "# Weekly Finance Ops Pack" in body
    assert "Invoice Summary" in body
    assert "Exceptions Breakdown" in body
    assert "Recommended Actions" in body


def test_weekly_pack_creates_audit_event(client, auth_headers, upload_dir):
    week_start = date.today() - timedelta(days=7)
    client.get(f"/weekly-pack.md?week_start={week_start}", headers=auth_headers)
    audit = client.get("/audit", headers=auth_headers).json()
    assert any(e["event_type"] == "WEEKLY_PACK_GENERATED" for e in audit)


def test_weekly_pack_requires_auth(client, upload_dir):
    resp = client.get(f"/weekly-pack.md?week_start=2024-01-01")
    assert resp.status_code == 401
