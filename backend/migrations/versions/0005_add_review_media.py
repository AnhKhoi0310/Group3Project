"""Add reviewer avatar and review photo URLs.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews", sa.Column("reviewer_avatar_url", sa.String(1024), nullable=True)
    )
    op.add_column("reviews", sa.Column("image_urls", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reviews", "image_urls")
    op.drop_column("reviews", "reviewer_avatar_url")
