"""add_market_breadth

Revision ID: c1d2e3f4a5b6
Revises: a9b8c7d6e5f4
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_breadth",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("signal_scans.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_symbols", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pct_above_sma50", sa.Float(), nullable=True),
        sa.Column("advancers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decliners", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_highs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("market_breadth")
