"""add_watchlist_notes_and_tags

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("watchlists", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("watchlists", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("watchlists", "tags")
    op.drop_column("watchlists", "note")
