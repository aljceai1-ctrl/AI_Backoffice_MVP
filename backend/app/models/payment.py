import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    paid_currency: Mapped[str] = mapped_column(String(10), default="AED")
    paid_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    payment_method: Mapped[str] = mapped_column(String(100), default="")
    reference: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    invoice = relationship("Invoice", back_populates="payments")
