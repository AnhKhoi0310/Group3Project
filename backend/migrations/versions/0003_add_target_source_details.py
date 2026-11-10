
"""Add platform and source URL to analysis targets."""

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
            "platform",
            sa.String(length=50),
            nullable=False,
            server_default="google_maps",
        ),
    )

    op.add_column(
        "analysis_targets",
        sa.Column(
            "source_url",
            sa.String(length=2048),
            nullable=True,
        ),
    )

    op.alter_column(
        "analysis_targets",
        "platform",
        existing_type=sa.String(length=50),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("analysis_targets", "source_url")
    op.drop_column("analysis_targets", "platform")
