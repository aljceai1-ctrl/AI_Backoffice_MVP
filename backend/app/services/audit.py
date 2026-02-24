"""Audit logging helper service."""
import uuid

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def log_event(
    db: Session,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    actor_user_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )
    db.add(event)
    return event
