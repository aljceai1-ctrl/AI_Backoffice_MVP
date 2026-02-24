import uuid
from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inbound_email_alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    allowed_currencies: Mapped[str] = mapped_column(String(255), default="AED,USD,EUR,GBP")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    users = relationship("User", back_populates="tenant", lazy="selectin")
    invoices = relationship("Invoice", back_populates="tenant", lazy="dynamic")
