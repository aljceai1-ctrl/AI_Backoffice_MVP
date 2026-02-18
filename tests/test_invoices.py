"""Tests for invoice lifecycle endpoints."""

import io
import uuid

import pytest

from tests.conftest import make_fake_file


# ─── Upload ──────────────────────────────────────────────────────────────────


def test_upload_creates_invoice_and_audit(client, auth_headers, upload_dir):
    resp = client.post(
        "/invoices/upload",
        headers=auth_headers,
        files=[make_fake_file()],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "NEW"
    assert data["filename"] == "invoice.pdf"
    assert "id" in data

    # Verify audit event was created
    invoice_id = data["id"]
    audit_resp = client.get(
        f"/audit?entity_id={invoice_id}", headers=auth_headers
    )
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert any(e["event_type"] == "INVOICE_UPLOADED" for e in events)


def test_upload_requires_auth(client, upload_dir):
    resp = client.post(
        "/invoices/upload",
        files=[make_fake_file()],
    )
    assert resp.status_code == 401


# ─── Extract ─────────────────────────────────────────────────────────────────


def _upload_invoice(client, auth_headers, upload_dir):
    resp = client.post(
        "/invoices/upload",
        headers=auth_headers,
        files=[make_fake_file()],
    )
    assert resp.status_code == 201
    return resp.json()


def test_extract_updates_invoice_and_audit(client, auth_headers, upload_dir):
    inv = _upload_invoice(client, auth_headers, upload_dir)
    invoice_id = inv["id"]

    payload = {
        "vendor": "ACME Corp",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": "5000.00",
        "currency": "AED",
    }
    resp = client.post(
        f"/invoices/{invoice_id}/extract",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "EXTRACTED"
    assert data["vendor"] == "ACME Corp"
    assert data["currency"] == "AED"

    # Audit check
    audit_resp = client.get(f"/audit?entity_id={invoice_id}", headers=auth_headers)
    events = audit_resp.json()
    assert any(e["event_type"] == "INVOICE_EXTRACTED" for e in events)


def test_extract_partial_update(client, auth_headers, upload_dir):
    inv = _upload_invoice(client, auth_headers, upload_dir)
    resp = client.post(
        f"/invoices/{inv['id']}/extract",
        headers=auth_headers,
        json={"vendor": "Partial Vendor"},
    )
    assert resp.status_code == 200
    assert resp.json()["vendor"] == "Partial Vendor"
    assert resp.json()["status"] == "EXTRACTED"


# ─── Validate ────────────────────────────────────────────────────────────────


def _extract_invoice(client, auth_headers, upload_dir, fields=None):
    inv = _upload_invoice(client, auth_headers, upload_dir)
    invoice_id = inv["id"]
    default_fields = {
        "vendor": "Good Vendor",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-10",
        "due_date": "2024-02-10",
        "amount": "1000.00",
        "currency": "AED",
    }
    client.post(
        f"/invoices/{invoice_id}/extract",
        headers=auth_headers,
        json=fields or default_fields,
    )
    return invoice_id


def test_validate_clean_invoice_is_validated(client, auth_headers, upload_dir):
    invoice_id = _extract_invoice(client, auth_headers, upload_dir)
    resp = client.post(f"/invoices/{invoice_id}/validate", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "VALIDATED"

    # No blocking exceptions → no APPROVAL_PENDING
    detail = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    assert detail["exceptions"] == []


def test_validate_missing_field_creates_exception_and_pending(
    client, auth_headers, upload_dir
):
    invoice_id = _extract_invoice(
        client,
        auth_headers,
        upload_dir,
        fields={"vendor": "Incomplete Vendor"},  # missing required fields
    )
    resp = client.post(f"/invoices/{invoice_id}/validate", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVAL_PENDING"

    detail = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    types = [e["type"] for e in detail["exceptions"]]
    assert "MISSING_FIELD" in types


def test_validate_invalid_amount(client, auth_headers, upload_dir):
    invoice_id = _extract_invoice(
        client,
        auth_headers,
        upload_dir,
        fields={
            "vendor": "V",
            "invoice_number": "X",
            "invoice_date": "2024-01-01",
            "due_date": "2024-02-01",
            "amount": "-100",
            "currency": "AED",
        },
    )
    resp = client.post(f"/invoices/{invoice_id}/validate", headers=auth_headers)
    detail = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    assert any(e["type"] == "INVALID_AMOUNT" for e in detail["exceptions"])


def test_validate_invalid_currency(client, auth_headers, upload_dir):
    invoice_id = _extract_invoice(
        client,
        auth_headers,
        upload_dir,
        fields={
            "vendor": "V",
            "invoice_number": "Y",
            "invoice_date": "2024-01-01",
            "due_date": "2024-02-01",
            "amount": "500",
            "currency": "JPY",  # not in allowed set
        },
    )
    resp = client.post(f"/invoices/{invoice_id}/validate", headers=auth_headers)
    detail = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    assert any(e["type"] == "INVALID_CURRENCY" for e in detail["exceptions"])


def test_validate_duplicate_invoice(client, auth_headers, upload_dir):
    # Create first invoice (valid)
    _extract_invoice(
        client,
        auth_headers,
        upload_dir,
        fields={
            "vendor": "Dup Vendor",
            "invoice_number": "DUP-001",
            "invoice_date": "2024-01-01",
            "due_date": "2024-02-01",
            "amount": "1000",
            "currency": "AED",
        },
    )
    # Create second invoice with same vendor + number
    second_id = _extract_invoice(
        client,
        auth_headers,
        upload_dir,
        fields={
            "vendor": "Dup Vendor",
            "invoice_number": "DUP-001",
            "invoice_date": "2024-01-02",
            "due_date": "2024-02-02",
            "amount": "2000",
            "currency": "AED",
        },
    )
    resp = client.post(f"/invoices/{second_id}/validate", headers=auth_headers)
    detail = client.get(f"/invoices/{second_id}", headers=auth_headers).json()
    assert any(e["type"] == "DUPLICATE_INVOICE" for e in detail["exceptions"])


# ─── Approve ─────────────────────────────────────────────────────────────────


def _validated_invoice_id(client, auth_headers, upload_dir):
    invoice_id = _extract_invoice(client, auth_headers, upload_dir)
    client.post(f"/invoices/{invoice_id}/validate", headers=auth_headers)
    return invoice_id


def test_approve_sets_status_and_audit(client, auth_headers, upload_dir):
    invoice_id = _validated_invoice_id(client, auth_headers, upload_dir)
    resp = client.post(
        f"/invoices/{invoice_id}/approve",
        headers=auth_headers,
        json={"decision": "APPROVE", "decided_by": "Alice", "notes": "All good"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["decision"] == "APPROVE"

    inv = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    assert inv["status"] == "APPROVED"

    events = client.get(f"/audit?entity_id={invoice_id}", headers=auth_headers).json()
    assert any(e["event_type"] == "INVOICE_APPROVED" for e in events)
    approved_event = next(e for e in events if e["event_type"] == "INVOICE_APPROVED")
    assert approved_event["actor"] == "Alice"


def test_reject_sets_status(client, auth_headers, upload_dir):
    invoice_id = _validated_invoice_id(client, auth_headers, upload_dir)
    resp = client.post(
        f"/invoices/{invoice_id}/approve",
        headers=auth_headers,
        json={"decision": "REJECT", "decided_by": "Bob", "notes": "Wrong amount"},
    )
    assert resp.status_code == 200
    inv = client.get(f"/invoices/{invoice_id}", headers=auth_headers).json()
    assert inv["status"] == "REJECTED"


def test_approve_wrong_status_returns_409(client, auth_headers, upload_dir):
    inv = _upload_invoice(client, auth_headers, upload_dir)
    resp = client.post(
        f"/invoices/{inv['id']}/approve",
        headers=auth_headers,
        json={"decision": "APPROVE", "decided_by": "X"},
    )
    assert resp.status_code == 409


# ─── List ────────────────────────────────────────────────────────────────────


def test_list_invoices_filter_by_status(client, auth_headers, upload_dir):
    _upload_invoice(client, auth_headers, upload_dir)
    resp = client.get("/invoices?status=NEW", headers=auth_headers)
    assert resp.status_code == 200
    assert all(i["status"] == "NEW" for i in resp.json())
