"""Add platform, source_url and updated_at to analysis targets

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_targets",
        sa.Column(
            "platform", sa.String(50), nullable=False, server_default="google_maps"
        ),
    )
    op.add_column(
        "analysis_targets",
        sa.Column("source_url", sa.String(2048), nullable=False, server_default=""),
    )
    op.add_column(
        "analysis_targets",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.alter_column(
        "analysis_targets",
        "platform",
        existing_type=sa.String(50),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "analysis_targets",
        "source_url",
        existing_type=sa.String(2048),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("analysis_targets", "updated_at")
    op.drop_column("analysis_targets", "source_url")
    op.drop_column("analysis_targets", "platform")
