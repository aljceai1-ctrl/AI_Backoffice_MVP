import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, Enum):
    NEW = "NEW"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class InvoiceSource(str, Enum):
    UPLOAD = "UPLOAD"
    EMAIL = "EMAIL"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(255), default="")
    invoice_number: Mapped[str] = mapped_column(String(255), default="")
    invoice_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="AED")
    status: Mapped[str] = mapped_column(String(50), default=InvoiceStatus.NEW.value)
    file_path: Mapped[str] = mapped_column(Text, default="")
    original_filename: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(20), default=InvoiceSource.UPLOAD.value)
    source_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    tenant = relationship("Tenant", back_populates="invoices")
    exceptions = relationship("InvoiceException", back_populates="invoice", lazy="selectin")
    approvals = relationship("Approval", back_populates="invoice", lazy="selectin")
    payments = relationship("Payment", back_populates="invoice", lazy="selectin")
