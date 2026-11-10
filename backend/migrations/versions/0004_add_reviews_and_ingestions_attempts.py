"""Add persisted reviews and ingestion attempt state.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("source_review_id", sa.String(255), nullable=True),
        sa.Column("source_platform", sa.String(50), nullable=False),
        sa.Column("reviewer_name", sa.String(255), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("review_date", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["analysis_targets.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "target_id",
            "source_review_id",
            name="uq_reviews_target_source_review",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_reviews_target_id", "reviews", ["target_id"])

    op.create_table(
        "ingestion_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "reviews_found",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "reviews_skipped",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("failure_category", sa.String(50), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["analysis_targets.id"],
            ondelete="CASCADE",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_ingestion_attempts_target_id",
        "ingestion_attempts",
        ["target_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_attempts_target_id",
        table_name="ingestion_attempts",
    )
    op.drop_table("ingestion_attempts")
    op.drop_index("ix_reviews_target_id", table_name="reviews")
    op.drop_table("reviews")
