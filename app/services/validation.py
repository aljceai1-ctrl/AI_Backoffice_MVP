"""Validation service — enforces business rules and creates exceptions.

All validation rules are defined as small, independent functions that each
return a list of InvoiceException rows to add.  The orchestrator
``validate_invoice`` collects all exceptions, persists them, and advances
the invoice status.

Adding a new rule:
    1. Write a ``_check_<name>(db, invoice) -> list[InvoiceException]`` function.
    2. Register it in ``_RULES``.
That's it — no other changes required.
"""

import logging
from typing import Callable, List

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.exception import InvoiceException
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

# Exception types classified as blocking (require human approval)
_BLOCKING_TYPES = frozenset(
    ["MISSING_FIELD", "DUPLICATE_INVOICE", "INVALID_AMOUNT", "INVALID_CURRENCY"]
)


# ─── Individual rule checkers ────────────────────────────────────────────────


def _check_required_fields(db: Session, invoice: Invoice) -> List[InvoiceException]:
    """Flag any core field that is absent or blank."""
    required = ("vendor", "invoice_number", "invoice_date", "amount", "currency")
    exceptions: List[InvoiceException] = []
    for field in required:
        value = getattr(invoice, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            exceptions.append(
                _make_exception(
                    invoice,
                    type_="MISSING_FIELD",
                    message=f"Required field '{field}' is missing or blank.",
                )
            )
    return exceptions


def _check_amount(db: Session, invoice: Invoice) -> List[InvoiceException]:
    """Amount must be strictly positive."""
    if invoice.amount is not None and float(invoice.amount) <= 0:
        return [
            _make_exception(
                invoice,
                type_="INVALID_AMOUNT",
                message=f"Amount must be > 0; received {invoice.amount}.",
            )
        ]
    return []


def _check_currency(db: Session, invoice: Invoice) -> List[InvoiceException]:
    """Currency must be in the configured allowed set."""
    settings = get_settings()
    if invoice.currency and invoice.currency.upper() not in [
        c.upper() for c in settings.ALLOWED_CURRENCIES
    ]:
        return [
            _make_exception(
                invoice,
                type_="INVALID_CURRENCY",
                message=(
                    f"Currency '{invoice.currency}' is not permitted. "
                    f"Allowed: {', '.join(settings.ALLOWED_CURRENCIES)}."
                ),
            )
        ]
    return []


def _check_duplicate(db: Session, invoice: Invoice) -> List[InvoiceException]:
    """Same invoice_number for the same vendor must not already exist."""
    if not (invoice.vendor and invoice.invoice_number):
        return []
    duplicate = (
        db.query(Invoice)
        .filter(
            Invoice.vendor == invoice.vendor,
            Invoice.invoice_number == invoice.invoice_number,
            Invoice.id != invoice.id,
        )
        .first()
    )
    if duplicate:
        return [
            _make_exception(
                invoice,
                type_="DUPLICATE_INVOICE",
                message=(
                    f"Invoice number '{invoice.invoice_number}' for vendor "
                    f"'{invoice.vendor}' already exists (id={duplicate.id})."
                ),
            )
        ]
    return []


# Ordered list of rule functions to run
_RULES: List[Callable[[Session, Invoice], List[InvoiceException]]] = [
    _check_required_fields,
    _check_amount,
    _check_currency,
    _check_duplicate,
]


# ─── Orchestrator ────────────────────────────────────────────────────────────


def validate_invoice(db: Session, invoice: Invoice) -> List[InvoiceException]:
    """Run all validation rules against ``invoice``.

    Creates InvoiceException rows for every rule violation.
    Sets ``invoice.status`` to VALIDATED (clean) or APPROVAL_PENDING (issues).

    Args:
        db:      Active session.
        invoice: The invoice to validate.

    Returns:
        List of InvoiceException rows added (may be empty).
    """
    all_exceptions: List[InvoiceException] = []

    for rule in _RULES:
        exceptions = rule(db, invoice)
        for exc in exceptions:
            db.add(exc)
        all_exceptions.extend(exceptions)

    db.flush()

    has_blocking = any(e.type in _BLOCKING_TYPES for e in all_exceptions)
    invoice.status = "APPROVAL_PENDING" if has_blocking else "VALIDATED"
    db.flush()

    logger.info(
        "Invoice %s validated: %d exception(s), status → %s",
        invoice.id,
        len(all_exceptions),
        invoice.status,
    )
    return all_exceptions


# ─── Helper ──────────────────────────────────────────────────────────────────


def _make_exception(invoice: Invoice, *, type_: str, message: str) -> InvoiceException:
    return InvoiceException(
        invoice_id=invoice.id,
        type=type_,
        message=message,
        status="OPEN",
    )
