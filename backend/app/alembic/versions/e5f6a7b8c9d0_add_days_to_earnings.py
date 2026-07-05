"""add_days_to_earnings

Revision ID: e5f6a7b8c9d0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_results", sa.Column("days_to_earnings", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_results", "days_to_earnings")