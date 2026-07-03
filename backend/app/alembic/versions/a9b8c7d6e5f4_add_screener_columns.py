"""add_screener_columns

Revision ID: a9b8c7d6e5f4
Revises: f7a8b9c0d1e2
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCREENER_COLUMNS = (
    sa.Column("rsi", sa.Float(), nullable=True),
    sa.Column("sma20", sa.Float(), nullable=True),
    sa.Column("sma50", sa.Float(), nullable=True),
    sa.Column("volume_ratio", sa.Float(), nullable=True),
    sa.Column("pct_from_52w_high", sa.Float(), nullable=True),
    sa.Column("pct_change_1d", sa.Float(), nullable=True),
    sa.Column("sector", sa.String(), nullable=True),
)


def upgrade() -> None:
    for col in SCREENER_COLUMNS:
        op.add_column("scan_results", col)


def downgrade() -> None:
    for col in reversed(SCREENER_COLUMNS):
        op.drop_column("scan_results", col.name)
