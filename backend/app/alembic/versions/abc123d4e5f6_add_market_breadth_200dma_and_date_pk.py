"""add_market_breadth_200dma_and_date_pk

Revision ID: abc123d4e5f6
Revises: c1d2e3f4a5b6
Create Date: 2026-07-05 00:00:00.000000

Migrates market_breadth from:
  - id (auto-int PK)         -> date (Date PK, trading day)
  - total_symbols (unused)   -> dropped
  - pct_above_sma50          -> pct_above_50dma (rename)
  - new column: pct_above_200dma
  - new column: new_lows

This migration is DESTRUCTIVE of the existing data in market_breadth
because we are changing the primary key and dropping total_symbols.
Production deployments should run this during a low-traffic window.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "abc123d4e5f6"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The existing c1d2e3f4a5b6 migration creates the table with:
    #   id INTEGER PK, scan_id FK, total_symbols, pct_above_sma50,
    #   advancers, decliners, new_highs, computed_at
    #
    # We need to:
    # 1. Drop the old table (cascade deletes signal_scans rows too — signal
    #    scans will be re-computed by the nightly cron which re-creates the
    #    market_breadth rows with the new schema).
    # 2. Recreate with the new schema.
    #
    # Using drop+create rather than multi-step alter because SQLAlchemy/
    # Alembic cannot rename columns or change PK constraints cleanly in a
    # single alter-table statement on all supported DBs (SQLite needs a full
    # table rebuild for anything that changes the PK).
    op.drop_table("market_breadth")

    op.create_table(
        "market_breadth",
        sa.Column(
            "date",
            sa.Date(),
            primary_key=True,
        ),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("signal_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pct_above_50dma", sa.Float(), nullable=True),
        sa.Column("pct_above_200dma", sa.Float(), nullable=True),
        sa.Column("advancers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decliners", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_highs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_lows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Downgrade: recreate the old market_breadth table with the pre-migration
    # schema so that existing signal_scans FK references are still valid.
    # Note: data loss is expected on downgrade since pct_above_200dma,
    # new_lows, and total_symbols cannot all be restored from the new schema.
    op.drop_table("market_breadth")

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