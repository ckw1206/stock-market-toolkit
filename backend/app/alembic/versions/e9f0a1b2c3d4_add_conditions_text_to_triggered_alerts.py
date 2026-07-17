"""add_conditions_text_to_triggered_alerts

Multi-condition alerts stored threshold_value=0.0 on TriggeredAlert, so the
frontend triggered list showed a meaningless "threshold: $0". Store the
human-readable matched-conditions text at trigger time instead.

Revision ID: e9f0a1b2c3d4
Revises: d5e6f7a8b9c0
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "triggered_alerts",
        sa.Column("conditions_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("triggered_alerts", "conditions_text")
