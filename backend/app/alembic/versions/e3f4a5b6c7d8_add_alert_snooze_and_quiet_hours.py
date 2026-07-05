"""add_alert_snooze_and_quiet_hours

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notification_settings", sa.Column("quiet_start", sa.String(length=5), nullable=True))
    op.add_column("notification_settings", sa.Column("quiet_end", sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column("notification_settings", "quiet_end")
    op.drop_column("notification_settings", "quiet_start")
    op.drop_column("alerts", "snoozed_until")
