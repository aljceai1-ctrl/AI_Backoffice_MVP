"""Pydantic schemas for audit events."""

import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import ORMBase


class AuditEventResponse(ORMBase):
    id: uuid.UUID
    timestamp: datetime
    request_id: Optional[str]
    actor: str
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    source: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]
