"""Seed script: creates demo data for 2 tenants with users, invoices, payments, exceptions, audit events."""
import os
import random
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.ingestion_run import IngestionRun
from app.models.invoice import Invoice, InvoiceSource, InvoiceStatus
from app.models.invoice_exception import InvoiceException
from app.models.payment import Payment
from app.models.tenant import Tenant
from app.models.user import User

random.seed(42)

VENDORS = [
    "Emirates Steel", "Dubai Logistics Co", "Al Futtaim Services", "Noon Supplies",
    "RAK Ceramics", "DEWA Utilities", "Etisalat Telecom", "Gulf Packaging",
    "Mashreq Office Supplies", "Carrefour Business", "Aramex Shipping", "DP World Logistics",
]

EXCEPTION_CODES = ["MISSING_VENDOR", "MISSING_NUMBER", "MISSING_DATE", "MISSING_AMOUNT", "INVALID_AMOUNT", "INVALID_CURRENCY"]
STATUSES_FLOW = [InvoiceStatus.NEW, InvoiceStatus.VALIDATED, InvoiceStatus.APPROVAL_PENDING, InvoiceStatus.APPROVED, InvoiceStatus.PAID]
PAYMENT_METHODS = ["Bank Transfer", "Credit Card", "Wire Transfer", "Check"]


def random_date(start_days_ago: int = 180, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.now(UTC) - timedelta(days=delta, hours=random.randint(0, 23), minutes=random.randint(0, 59))


def seed():
    db = SessionLocal()

    # Check if already seeded
    if db.query(Tenant).first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    print("Seeding database...")

    # === Tenant 1: Acme Corp ===
    t1 = Tenant(id=uuid.uuid4(), name="Acme Corp", inbound_email_alias="acme")
    db.add(t1)

    # === Tenant 2: Gulf Trading LLC ===
    t2 = Tenant(id=uuid.uuid4(), name="Gulf Trading LLC", inbound_email_alias="gulftrading")
    db.add(t2)
    db.flush()

    # Users per tenant (password: "demo1234" for all)
    pw = hash_password("demo1234")

    users_t1 = [
        User(tenant_id=t1.id, email="admin@acme.com", password_hash=pw, full_name="Acme Admin", role="ADMIN"),
        User(tenant_id=t1.id, email="approver@acme.com", password_hash=pw, full_name="Sarah Approver", role="APPROVER"),
        User(tenant_id=t1.id, email="auditor@acme.com", password_hash=pw, full_name="Tom Auditor", role="AUDITOR"),
        User(tenant_id=t1.id, email="uploader@acme.com", password_hash=pw, full_name="Jane Uploader", role="UPLOADER"),
        User(tenant_id=t1.id, email="viewer@acme.com", password_hash=pw, full_name="Bob Viewer", role="VIEWER"),
    ]

    users_t2 = [
        User(tenant_id=t2.id, email="admin@gulf.local", password_hash=pw, full_name="Gulf Admin", role="ADMIN"),
        User(tenant_id=t2.id, email="approver@gulf.local", password_hash=pw, full_name="Omar Approver", role="APPROVER"),
    ]

    for u in users_t1 + users_t2:
        db.add(u)
    db.flush()

    # Generate invoices for both tenants
    all_invoices = []
    for tenant, users in [(t1, users_t1), (t2, users_t2)]:
        approver = next(u for u in users if u.role in ("APPROVER", "ADMIN"))
        admin = next(u for u in users if u.role == "ADMIN")

        for i in range(60):
            created = random_date(180, 1)
            vendor = random.choice(VENDORS)
            amount = round(random.uniform(500, 50000), 2)
            currency = random.choice(["AED", "USD", "EUR"])
            source = random.choice([InvoiceSource.UPLOAD.value, InvoiceSource.EMAIL.value])

            # Determine status based on age and randomness
            age_days = (datetime.now(UTC) - created).days
            if age_days > 120:
                status = random.choice([InvoiceStatus.PAID.value, InvoiceStatus.APPROVED.value, InvoiceStatus.REJECTED.value])
            elif age_days > 60:
                status = random.choice([InvoiceStatus.APPROVED.value, InvoiceStatus.APPROVAL_PENDING.value, InvoiceStatus.PAID.value])
            elif age_days > 14:
                status = random.choice([InvoiceStatus.VALIDATED.value, InvoiceStatus.APPROVAL_PENDING.value, InvoiceStatus.APPROVED.value])
            else:
                status = random.choice([InvoiceStatus.NEW.value, InvoiceStatus.VALIDATED.value, InvoiceStatus.APPROVAL_PENDING.value])

            inv = Invoice(
                tenant_id=tenant.id,
                vendor=vendor,
                invoice_number=f"INV-{tenant.name[:3].upper()}-{i+1:04d}",
                invoice_date=created.date() if random.random() > 0.1 else None,
                amount=amount if random.random() > 0.05 else None,
                currency=currency,
                status=status,
                file_path="",
                original_filename=f"invoice_{i+1}.pdf",
                source=source,
                created_at=created,
                updated_at=created + timedelta(hours=random.randint(1, 48)),
            )
            db.add(inv)
            db.flush()
            all_invoices.append((inv, tenant, approver, admin))

            # Add exceptions for ~40% of invoices
            if random.random() < 0.4:
                num_exc = random.randint(1, 3)
                for _ in range(num_exc):
                    code = random.choice(EXCEPTION_CODES)
                    exc_created = created + timedelta(minutes=random.randint(1, 30))
                    resolved_at = None
                    resolved_by = None
                    if status in (InvoiceStatus.APPROVED.value, InvoiceStatus.PAID.value, InvoiceStatus.REJECTED.value):
                        resolved_at = exc_created + timedelta(hours=random.randint(1, 72))
                        resolved_by = admin.id
                    exc = InvoiceException(
                        tenant_id=tenant.id,
                        invoice_id=inv.id,
                        code=code,
                        message=f"Validation failed: {code.replace('_', ' ').lower()}",
                        severity=random.choice(["ERROR", "WARNING"]),
                        created_at=exc_created,
                        resolved_at=resolved_at,
                        resolved_by_user_id=resolved_by,
                    )
                    db.add(exc)

            # Add approvals for approved/rejected/paid
            if status in (InvoiceStatus.APPROVED.value, InvoiceStatus.PAID.value, InvoiceStatus.REJECTED.value):
                decision = "REJECTED" if status == InvoiceStatus.REJECTED.value else "APPROVED"
                decided_at = created + timedelta(hours=random.randint(2, 96))
                db.add(Approval(
                    tenant_id=tenant.id,
                    invoice_id=inv.id,
                    decided_by_user_id=approver.id,
                    decision=decision,
                    decided_at=decided_at,
                    notes=random.choice(["Looks good", "Verified against PO", "Amount confirmed", ""]),
                ))

            # Add payments for paid invoices
            if status == InvoiceStatus.PAID.value:
                paid_at = created + timedelta(hours=random.randint(48, 240))
                db.add(Payment(
                    tenant_id=tenant.id,
                    invoice_id=inv.id,
                    paid_amount=amount if amount else round(random.uniform(500, 50000), 2),
                    paid_currency=currency,
                    paid_at=paid_at,
                    payment_method=random.choice(PAYMENT_METHODS),
                    reference=f"PAY-{random.randint(10000, 99999)}",
                    created_by_user_id=admin.id,
                ))

    # Audit events
    actions = ["LOGIN", "INVOICE_UPLOADED", "INVOICE_APPROVED", "INVOICE_REJECTED",
               "INVOICE_PAID", "EMAIL_RECEIVED", "USER_CREATED", "INVOICE_AUTO_EXTRACTED"]
    for tenant, users in [(t1, users_t1), (t2, users_t2)]:
        for _ in range(100):
            ts = random_date(180, 1)
            action = random.choice(actions)
            actor = random.choice(users)
            db.add(AuditEvent(
                tenant_id=tenant.id,
                timestamp=ts,
                actor_user_id=actor.id,
                action=action,
                entity_type=random.choice(["invoice", "user", "payment"]),
                entity_id=str(uuid.uuid4()),
                metadata_json={"source": "seed"},
            ))

    # Ingestion runs
    for tenant in [t1, t2]:
        for day_offset in range(90):
            for _ in range(random.randint(1, 4)):
                started = datetime.now(UTC) - timedelta(days=day_offset, hours=random.randint(0, 23))
                emails_seen = random.randint(0, 5)
                failures = random.randint(0, 1) if random.random() < 0.15 else 0
                processed = max(0, emails_seen - failures)
                db.add(IngestionRun(
                    tenant_id=tenant.id,
                    provider="MAILHOG",
                    run_started_at=started,
                    run_finished_at=started + timedelta(seconds=random.randint(2, 30)),
                    emails_seen=emails_seen,
                    emails_processed=processed,
                    invoices_created=processed,
                    failures_count=failures,
                    retries_count=random.randint(0, 2) if failures > 0 else 0,
                    status="SUCCESS" if failures == 0 else "PARTIAL",
                    last_error="Connection timeout" if failures > 0 else None,
                ))

    db.commit()
    db.close()
    print("Seed complete! Demo users (password: demo1234):")
    print("  Acme Corp:         admin@acme.com, approver@acme.com, auditor@acme.com, uploader@acme.com, viewer@acme.com")
    print("  Gulf Trading LLC:  admin@gulf.local, approver@gulf.local")


if __name__ == "__main__":
    seed()
