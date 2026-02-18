"""Approval service — processes human approve/reject decisions."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.approval import Approval
from app.models.invoice import Invoice
from app.schemas.approval import ApprovalRequest

logger = logging.getLogger(__name__)


def process_approval(
    db: Session, invoice: Invoice, req: ApprovalRequest
) -> Approval:
    """Record a human decision and advance the invoice to APPROVED or REJECTED.

    This is the only code path that sets terminal invoice statuses.
    No payment is executed — this system is export-only.

    Args:
        db:      Active session.
        invoice: Invoice being decided on.
        req:     Validated approval payload (decision, decided_by, notes).

    Returns:
        The flushed Approval record.
    """
    decision = req.decision.upper()
    now = datetime.now(UTC)

    approval = Approval(
        invoice_id=invoice.id,
        decision=decision,
        decided_by=req.decided_by,
        decided_at=now,
        notes=req.notes,
    )
    db.add(approval)

    invoice.status = "APPROVED" if decision == "APPROVE" else "REJECTED"
    db.flush()

    logger.info(
        "Invoice %s → %s (by %s)",
        invoice.id,
        invoice.status,
        req.decided_by,
    )
    return approval
