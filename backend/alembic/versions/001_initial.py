"""Initial schema: all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("inbound_email_alias", sa.String(255), unique=True, nullable=False),
        sa.Column("allowed_currencies", sa.String(255), server_default="AED,USD,EUR,GBP"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), server_default=""),
        sa.Column("role", sa.String(50), server_default="VIEWER"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Invoices
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("vendor", sa.String(255), server_default=""),
        sa.Column("invoice_number", sa.String(255), server_default=""),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(10), server_default="AED"),
        sa.Column("status", sa.String(50), server_default="NEW"),
        sa.Column("file_path", sa.Text(), server_default=""),
        sa.Column("original_filename", sa.String(500), server_default=""),
        sa.Column("source", sa.String(20), server_default="UPLOAD"),
        sa.Column("source_message_id", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False, index=True),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_currency", sa.String(10), server_default="AED"),
        sa.Column("paid_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("payment_method", sa.String(100), server_default=""),
        sa.Column("reference", sa.Text(), server_default=""),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Invoice exceptions
    op.create_table(
        "invoice_exceptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False, index=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), server_default="ERROR"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    # Approvals
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False, index=True),
        sa.Column("decided_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), server_default=""),
    )

    # Audit events
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), server_default=""),
        sa.Column("entity_id", sa.String(100), server_default=""),
        sa.Column("metadata", JSONB, nullable=True),
    )

    # Ingestion runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("provider", sa.String(50), server_default="MAILHOG"),
        sa.Column("run_started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("run_finished_at", sa.DateTime(), nullable=True),
        sa.Column("emails_seen", sa.Integer(), server_default="0"),
        sa.Column("emails_processed", sa.Integer(), server_default="0"),
        sa.Column("invoices_created", sa.Integer(), server_default="0"),
        sa.Column("failures_count", sa.Integer(), server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retries_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="SUCCESS"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("audit_events")
    op.drop_table("approvals")
    op.drop_table("invoice_exceptions")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("users")
    op.drop_table("tenants")
