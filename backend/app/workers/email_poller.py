"""Email ingestion worker: polls MailHog API and creates invoices from attachments."""
import base64
import email as email_lib
import logging
import os
import uuid
from datetime import UTC, datetime
from email.policy import default as default_policy

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.ingestion_run import IngestionRun
from app.models.invoice import Invoice, InvoiceSource, InvoiceStatus
from app.models.invoice_exception import InvoiceException
from app.models.tenant import Tenant
from app.services.validation import validate_invoice

logger = logging.getLogger(__name__)


class MailHogProvider:
    """Polls MailHog API v2 for new messages."""

    def __init__(self, api_url: str = ""):
        self.api_url = api_url or settings.MAILHOG_API_URL

    def fetch_messages(self) -> list[dict]:
        try:
            resp = httpx.get(f"{self.api_url}/messages", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except Exception as e:
            logger.error("MailHog fetch error: %s", e)
            return []

    def delete_message(self, message_id: str):
        try:
            httpx.delete(f"{self.api_url.replace('/v2', '/v1')}/messages/{message_id}", timeout=10)
        except Exception as e:
            logger.warning("Failed to delete message %s: %s", message_id, e)


def _extract_to_address(msg: dict) -> str:
    """Extract the 'To' address from a MailHog message.

    Supports three sources (in priority order):
    1. Top-level To array: [{"Mailbox": "alias", "Domain": "example.com"}]
       - Domain may be empty for alias-only recipients.
    2. Content.Headers.To header string.
    3. Empty string as last resort.
    """
    # 1) MailHog structured To array (always present, even when MIME is null)
    to_array = msg.get("To")
    if to_array and isinstance(to_array, list):
        first = to_array[0]
        if isinstance(first, dict):
            mailbox = (first.get("Mailbox") or "").strip()
            domain = (first.get("Domain") or "").strip()
            if mailbox:
                return f"{mailbox}@{domain}".lower() if domain else mailbox.lower()

    # 2) Content.Headers.To
    content = msg.get("Content") or {}
    headers = content.get("Headers") or {}
    to_list = headers.get("To", [])
    if to_list:
        addr = to_list[0]
        if "<" in addr:
            addr = addr.split("<")[1].split(">")[0]
        return addr.strip().lower()

    return ""


def _find_tenant_by_inbound(db: Session, address: str) -> Tenant | None:
    """Map an inbound email address to a tenant."""
    alias = address.split("@")[0] if "@" in address else address
    return db.query(Tenant).filter(Tenant.inbound_email_alias == alias).first()


def _save_attachment(content_bytes: bytes, filename: str) -> str:
    """Save attachment to upload directory, return file path."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1] if filename else ".bin"
    path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    with open(path, "wb") as f:
        f.write(content_bytes)
    return path


def _extract_attachments_from_mime(msg: dict) -> list[tuple[str, bytes]]:
    """Extract (filename, content_bytes) from MailHog MIME parts. Returns [] on None/missing."""
    mime = msg.get("MIME")
    if mime is None:
        return []
    parts = mime.get("Parts") if isinstance(mime, dict) else None
    if not parts:
        return []

    attachments: list[tuple[str, bytes]] = []
    for part in parts:
        headers = part.get("Headers") or {}
        content_disp = (headers.get("Content-Disposition") or [""])[0]
        content_type = (headers.get("Content-Type") or [""])[0]

        if "attachment" not in content_disp.lower() and "application/pdf" not in content_type.lower():
            continue

        filename = "attachment.pdf"
        if 'filename="' in content_disp:
            filename = content_disp.split('filename="')[1].split('"')[0]

        body = part.get("Body", "")
        content_encoding = (headers.get("Content-Transfer-Encoding") or [""])[0]

        if content_encoding.lower() == "base64":
            file_bytes = base64.b64decode(body)
        else:
            file_bytes = body.encode("utf-8") if isinstance(body, str) else body

        attachments.append((filename, file_bytes))
    return attachments


def _extract_attachments_from_raw(msg: dict) -> list[tuple[str, bytes]]:
    """Parse attachments from Raw.Data RFC822 message using Python's email parser."""
    raw = msg.get("Raw")
    if not raw or not isinstance(raw, dict):
        return []
    data = raw.get("Data")
    if not data:
        return []

    parsed = email_lib.message_from_string(data, policy=default_policy)
    attachments: list[tuple[str, bytes]] = []
    for part in parsed.walk():
        content_disp = part.get("Content-Disposition", "")
        content_type = part.get_content_type() or ""
        if "attachment" in content_disp.lower() or "application/pdf" in content_type.lower():
            payload = part.get_payload(decode=True)
            if payload:
                filename = part.get_filename() or "attachment.pdf"
                attachments.append((filename, payload))
    return attachments


def _extract_attachments(msg: dict) -> list[tuple[str, bytes]]:
    """Try MIME parts first, fall back to Raw.Data RFC822 parsing, then Content fallback."""
    attachments = _extract_attachments_from_mime(msg)
    if attachments:
        return attachments

    # Prefer Raw.Data for full RFC822 parsing when MIME is null/empty
    attachments = _extract_attachments_from_raw(msg)
    if attachments:
        return attachments

    # Last resort: Content.Body (plain body, no structured MIME)
    content = msg.get("Content") or {}
    body = content.get("Body", "")
    if body:
        logger.debug("Message has Content.Body but no extractable attachments")

    return []


def poll_and_ingest():
    """Main poll cycle: fetch messages from MailHog, create invoices."""
    provider = MailHogProvider()
    db = SessionLocal()
    run = IngestionRun(provider="MAILHOG", run_started_at=datetime.now(UTC))
    # Initialise counters eagerly so += never hits None
    run.emails_seen = 0
    run.emails_processed = 0
    run.invoices_created = 0
    run.failures_count = 0
    run.retries_count = 0

    try:
        messages = provider.fetch_messages()
        run.emails_seen = len(messages)
        invoices_created = 0
        failures = 0

        for msg in messages:
            msg_id = msg.get("ID", "")
            try:
                to_addr = _extract_to_address(msg)
                tenant = _find_tenant_by_inbound(db, to_addr)

                if not tenant:
                    logger.warning("No tenant for inbound address: %s", to_addr)
                    failures += 1
                    continue

                run.tenant_id = tenant.id

                # Extract attachments: MIME parts → Raw.Data RFC822 → empty
                attachments = _extract_attachments(msg)
                if not attachments:
                    # No attachments — still count as processed
                    run.emails_processed += 1
                    provider.delete_message(msg_id)
                    continue

                for filename, file_bytes in attachments:
                    file_path = _save_attachment(file_bytes, filename)

                    inv = Invoice(
                        tenant_id=tenant.id,
                        vendor="",
                        file_path=file_path,
                        original_filename=filename,
                        source=InvoiceSource.EMAIL.value,
                        source_message_id=msg_id,
                        status=InvoiceStatus.NEW.value,
                    )
                    db.add(inv)
                    db.flush()

                    exceptions = validate_invoice(inv, tenant)
                    for exc in exceptions:
                        exc.tenant_id = tenant.id
                        db.add(exc)

                    if exceptions:
                        inv.status = InvoiceStatus.VALIDATED.value
                    else:
                        inv.status = InvoiceStatus.APPROVAL_PENDING.value

                    db.add(AuditEvent(
                        tenant_id=tenant.id,
                        action="EMAIL_RECEIVED",
                        entity_type="invoice",
                        entity_id=str(inv.id),
                        metadata_json={"filename": filename, "from_email": to_addr, "message_id": msg_id},
                    ))
                    invoices_created += 1

                run.emails_processed += 1
                provider.delete_message(msg_id)

            except Exception as e:
                logger.error("Error processing message %s: %s", msg_id, e)
                failures += 1
                run.retries_count += 1

        run.invoices_created = invoices_created
        run.failures_count = failures
        run.status = "SUCCESS" if failures == 0 else ("PARTIAL" if invoices_created > 0 else "FAIL")
        run.run_finished_at = datetime.now(UTC)
        if failures > 0:
            run.last_error = f"{failures} message(s) failed to process"

        db.add(run)
        db.commit()
        logger.info("Ingestion run complete: %d seen, %d processed, %d invoices, %d failures",
                     run.emails_seen, run.emails_processed, invoices_created, failures)

    except Exception as e:
        logger.error("Ingestion run failed: %s", e)
        run.status = "FAIL"
        run.last_error = str(e)
        run.run_finished_at = datetime.now(UTC)
        db.add(run)
        db.commit()
    finally:
        db.close()
