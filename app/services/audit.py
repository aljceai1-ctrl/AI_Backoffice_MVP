"""Audit service — records immutable state-change events."""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


def record_event(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor: str = "system",
    request_id: Optional[str] = None,
    source: Optional[str] = None,
    confidence: Optional[float] = None,
    notes: Optional[str] = None,
) -> AuditEvent:
    """Append an audit event row for a meaningful state change.

    Must be called inside an active transaction; the caller is responsible
    for calling ``db.commit()`` after all related changes are flushed.

    Args:
        db:          Active SQLAlchemy session.
        event_type:  Human-readable action label (e.g. INVOICE_UPLOADED).
        entity_type: Affected resource type (e.g. "invoice").
        entity_id:   UUID of the affected resource.
        actor:       Identifier of the initiating user or "system".
        request_id:  Tracing ID from middleware (UUID string).
        source:      Origin of data (e.g. "manual", "ocr", "llm").
        confidence:  Float 0–1 extraction confidence, where applicable.
        notes:       Freeform context string.

    Returns:
        The flushed (but not yet committed) AuditEvent instance.
    """
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        request_id=request_id,
        source=source,
        confidence=confidence,
        notes=notes,
    )
    db.add(event)
    db.flush()

    logger.info(
        "Audit: %s on %s/%s by %s",
        event_type,
        entity_type,
        entity_id,
        actor,
        extra={"request_id": request_id},
    )
    return event
