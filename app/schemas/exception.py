"""Pydantic schemas for invoice exceptions."""

import uuid
from datetime import datetime

from app.schemas.common import ORMBase


class ExceptionResponse(ORMBase):
    id: uuid.UUID
    created_at: datetime
    invoice_id: uuid.UUID
    type: str
    message: str
    status: str
