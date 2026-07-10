"""multi_channel_discord_webhooks

Discord notifications supported exactly one webhook URL. This replaces the
single `discord_webhook_url` column with `discord_webhook_urls`, a JSON list,
so a user can fan a triggered alert out to several channels.

Revision ID: d5e6f7a8b9c0
Revises: fb1c2d3e4f5a
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "fb1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_settings",
        sa.Column("discord_webhook_urls", sa.JSON(), nullable=True),
    )

    bind = op.get_bind()
    ns = sa.table(
        "notification_settings",
        sa.column("user_id", sa.String),
        sa.column("discord_webhook_url", sa.Text),
        sa.column("discord_webhook_urls", sa.JSON),
    )
    rows = bind.execute(sa.select(ns.c.user_id, ns.c.discord_webhook_url)).fetchall()
    for user_id, url in rows:
        bind.execute(
            ns.update()
            .where(ns.c.user_id == user_id)
            .values(discord_webhook_urls=[url] if url else [])
        )

    op.drop_column("notification_settings", "discord_webhook_url")


def downgrade() -> None:
    op.add_column(
        "notification_settings",
        sa.Column("discord_webhook_url", sa.Text(), nullable=True),
    )

    bind = op.get_bind()
    ns = sa.table(
        "notification_settings",
        sa.column("user_id", sa.String),
        sa.column("discord_webhook_url", sa.Text),
        sa.column("discord_webhook_urls", sa.JSON),
    )
    rows = bind.execute(sa.select(ns.c.user_id, ns.c.discord_webhook_urls)).fetchall()
    for user_id, urls in rows:
        bind.execute(
            ns.update()
            .where(ns.c.user_id == user_id)
            .values(discord_webhook_url=(urls or [None])[0])
        )

    op.drop_column("notification_settings", "discord_webhook_urls")
