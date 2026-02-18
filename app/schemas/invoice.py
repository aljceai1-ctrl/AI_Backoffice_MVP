"""Pydantic schemas for invoices."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.approval import ApprovalResponse
from app.schemas.common import ORMBase
from app.schemas.exception import ExceptionResponse


class InvoiceExtract(ORMBase):
    """Fields submitted via the manual extraction endpoint.

    All fields are optional so partial updates are allowed.
    When LLM/OCR extraction is implemented, it should produce the same shape.
    """

    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None


class InvoiceResponse(ORMBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    filename: str
    storage_path: str
    vendor: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    amount: Optional[Decimal]
    currency: Optional[str]
    status: str
    extracted_json: Optional[Dict[str, Any]]


class InvoiceDetail(InvoiceResponse):
    """Extended invoice view including related exceptions and approvals."""

    exceptions: List[ExceptionResponse] = []
    approvals: List[ApprovalResponse] = []
