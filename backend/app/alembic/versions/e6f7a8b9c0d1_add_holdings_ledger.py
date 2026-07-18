"""add_holdings_ledger

Revision ID: e6f7a8b9c0d1
Revises: e9f0a1b2c3d4
Create Date: 2026-07-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("qty", sa.String(), nullable=True),
        sa.Column("price", sa.String(), nullable=True),
        sa.Column("amount", sa.String(), nullable=True),
        sa.Column("fee", sa.String(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_portfolio_transactions_user_id", "portfolio_transactions", ["user_id"]
    )
    op.create_table(
        "portfolio_suggestion_dismissals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("user_id", "symbol", "type", "ex_date",
                            name="uq_portfolio_dismissal"),
    )
    op.create_index(
        "ix_portfolio_suggestion_dismissals_user_id",
        "portfolio_suggestion_dismissals",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_suggestion_dismissals_user_id")
    op.drop_table("portfolio_suggestion_dismissals")
    op.drop_index("ix_portfolio_transactions_user_id")
    op.drop_table("portfolio_transactions")
