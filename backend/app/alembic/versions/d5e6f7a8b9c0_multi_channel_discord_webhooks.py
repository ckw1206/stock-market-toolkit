"""multi_channel_discord_webhooks

Discord notifications supported exactly one webhook URL. This adds
`discord_webhook_urls`, a JSON list, so a user can fan a triggered alert
out to several channels.

Expand-only: the legacy `discord_webhook_url` column is deliberately KEPT
(and dual-written by the settings route) so rolling back the app image past
this release still finds the column and current data. Drop it in a later
contract migration once no deployed code reads it.

NOT NULL + server_default '[]' matters for rolling deploys: a row inserted
by old code (which doesn't know this column) must land as [] rather than
NULL, because the response schema types the field as a non-optional list.

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
        sa.Column(
            "discord_webhook_urls",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )

    bind = op.get_bind()
    ns = sa.table(
        "notification_settings",
        sa.column("user_id", sa.String),
        sa.column("discord_webhook_url", sa.Text),
        sa.column("discord_webhook_urls", sa.JSON),
    )
    rows = bind.execute(
        sa.select(ns.c.user_id, ns.c.discord_webhook_url).where(
            ns.c.discord_webhook_url.isnot(None)
        )
    ).fetchall()
    for user_id, url in rows:
        if url:
            bind.execute(
                ns.update()
                .where(ns.c.user_id == user_id)
                .values(discord_webhook_urls=[url])
            )


def downgrade() -> None:
    # Legacy column still exists and is dual-written, so nothing to copy back.
    op.drop_column("notification_settings", "discord_webhook_urls")
