"""add_signal_scans

Revision ID: f7a8b9c0d1e2
Revises: 1d443507a293
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "1d443507a293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_scans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_run_id",
            sa.Integer(),
            sa.ForeignKey("job_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("signal_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(), nullable=False, index=True),
        sa.Column("signal", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("rvol", sa.Float(), nullable=True),
        sa.Column("breakout", sa.Boolean(), default=False),
        sa.Column("volume_spike", sa.Boolean(), default=False),
        sa.Column("reasons", sa.JSON(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scan_results")
    op.drop_table("signal_scans")