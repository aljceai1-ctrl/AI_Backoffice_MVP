"""Pydantic schemas for approvals."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import ORMBase


class ApprovalRequest(ORMBase):
    """Payload for POST /invoices/{id}/approve."""

    decision: str = Field(..., pattern="^(APPROVE|REJECT)$", description="APPROVE or REJECT")
    decided_by: str = Field(..., min_length=1, description="Name or ID of the approver")
    notes: Optional[str] = Field(None, description="Optional freeform notes")


class ApprovalResponse(ORMBase):
    id: uuid.UUID
    created_at: datetime
    decided_at: Optional[datetime]
    invoice_id: uuid.UUID
    decision: str
    decided_by: str
    notes: Optional[str]
