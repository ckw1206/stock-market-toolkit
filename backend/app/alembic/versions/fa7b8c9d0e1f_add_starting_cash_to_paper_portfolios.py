"""add_starting_cash_to_paper_portfolios

Revision ID: fa7b8c9d0e1f
Revises: f4a5b6c7d8e9
Create Date: 2026-07-05 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "fa7b8c9d0e1f"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "paper_portfolios",
        sa.Column("starting_cash", sa.Numeric(), nullable=False, server_default=text("100000.0")),
    )


def downgrade() -> None:
    op.drop_column("paper_portfolios", "starting_cash")