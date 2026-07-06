"""merge starting_cash and watchlist-notes heads

The starting_cash migration (fa7b8c9d0e1f) branches off the paper_trading
table migration (d2e3f4a5b6c7), independently of the watchlist-notes head
(f4a5b6c7d8e9). This merge reunites the two heads into a single line.

It also heals databases that were migrated by an earlier, forked version of
this branch: those had both f4a5b6c7d8e9 and fa7b8c9d0e1f stamped into
alembic_version as separate heads. Once fa7b8c9d0e1f became a descendant of
f4a5b6c7d8e9 the two overlapped and Alembic refused to start ("Requested
revision ... overlaps"). Merging them collapses both stamped rows into this
single revision. No DDL — the columns already exist in every reachable state.

Revision ID: fb1c2d3e4f5a
Revises: f4a5b6c7d8e9, fa7b8c9d0e1f
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "fb1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = ("f4a5b6c7d8e9", "fa7b8c9d0e1f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
