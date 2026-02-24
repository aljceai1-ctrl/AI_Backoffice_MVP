"""Audit log endpoints."""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.user import Role, User
from app.schemas.audit import AuditEventResponse

router = APIRouter(prefix="/audit", tags=["audit"])

AUDIT_ROLES = [Role.ADMIN.value, Role.AUDITOR.value, Role.APPROVER.value]


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    action: str | None = None,
    entity_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUDIT_ROLES)),
):
    q = db.query(AuditEvent).filter(AuditEvent.tenant_id == current_user.tenant_id)
    if action:
        q = q.filter(AuditEvent.action == action)
    if entity_type:
        q = q.filter(AuditEvent.entity_type == entity_type)
    if from_date:
        try:
            fd = date.fromisoformat(from_date)
            q = q.filter(AuditEvent.timestamp >= datetime(fd.year, fd.month, fd.day, tzinfo=UTC))
        except ValueError:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date)
            q = q.filter(AuditEvent.timestamp <= datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC))
        except ValueError:
            pass

    events = q.order_by(AuditEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [
        AuditEventResponse(
            id=str(e.id),
            tenant_id=str(e.tenant_id),
            timestamp=e.timestamp.isoformat() if e.timestamp else "",
            actor_user_id=str(e.actor_user_id) if e.actor_user_id else None,
            action=e.action,
            entity_type=e.entity_type or "",
            entity_id=e.entity_id or "",
            metadata_json=e.metadata_json,
        )
        for e in events
    ]
