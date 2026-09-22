"""persist trading orders

Revision ID: 02
Revises: 01
Create Date: 2026-09-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "02"
down_revision: str | None = "01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("executed_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("client_order_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rejection_reason", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_order_id"),
    )
    op.create_index(
        op.f("ix_trade_orders_client_order_id"),
        "trade_orders",
        ["client_order_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trade_orders_client_order_id"), table_name="trade_orders")
    op.drop_table("trade_orders")
