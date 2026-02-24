"""Add email metadata columns to invoices table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("email_subject", sa.String(1000), nullable=True))
    op.add_column("invoices", sa.Column("email_from", sa.String(500), nullable=True))
    op.add_column("invoices", sa.Column("attachment_count", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("invoices", "attachment_count")
    op.drop_column("invoices", "email_from")
    op.drop_column("invoices", "email_subject")
