"""Invoice exception ORM model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvoiceException(Base):
    """Records a validation problem found on an invoice.

    Exception types (non-exhaustive):
        MISSING_FIELD, DUPLICATE_INVOICE, INVALID_AMOUNT, INVALID_CURRENCY

    Status: OPEN (unresolved) | RESOLVED
    """

    __tablename__ = "invoice_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    __table_args__ = (
        Index("ix_invoice_exceptions_invoice_id", "invoice_id"),
    )
