"""Audit log query endpoint."""

import uuid
from datetime import date, datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_api_key
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventResponse

router = APIRouter(tags=["Audit"])

DB = Annotated[Session, Depends(get_db)]
Auth = Annotated[str, Depends(require_api_key)]


@router.get(
    "/audit",
    response_model=List[AuditEventResponse],
    summary="Query the audit log",
)
async def list_audit_events(
    db: DB,
    auth: Auth,
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by entity UUID"),
    from_date: Optional[date] = Query(None, alias="from", description="Events on or after (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="Events on or before (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
) -> List[AuditEvent]:
    """Return audit events, newest first.  Defaults to the latest 100 rows."""
    q = db.query(AuditEvent)

    if entity_id:
        q = q.filter(AuditEvent.entity_id == entity_id)
    if from_date:
        from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc)
        q = q.filter(AuditEvent.timestamp >= from_dt)
    if to_date:
        to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=timezone.utc)
        q = q.filter(AuditEvent.timestamp <= to_dt)

    return q.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
