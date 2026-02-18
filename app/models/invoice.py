"""Invoice ORM model."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Invoice(Base):
    """Represents an uploaded invoice moving through the processing pipeline.

    Status progression:
        NEW → EXTRACTED → VALIDATED → (APPROVAL_PENDING) → APPROVED | REJECTED
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # File reference — binary is stored on disk, never in DB
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Extracted invoice fields
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NEW", index=False
    )
    extracted_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_invoice_number", "invoice_number"),
    )
