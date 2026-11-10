from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

PLATFORM_GOOGLE_MAPS = "google_maps"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Firebase UIDs are case-sensitive, but MySQL's default collation is not.
    firebase_uid: Mapped[str] = mapped_column(
        String(128, collation="utf8mb4_bin"), unique=True
    )
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AnalysisTarget(Base):
    __tablename__ = "analysis_targets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Review(Base):
    """A normalized review owned transitively through its analysis target."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "target_id",
            "source_review_id",
            name="uq_reviews_target_source_review",
        ),
        Index("ix_reviews_target_id", "target_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("analysis_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_review_id: Mapped[str | None] = mapped_column(String(255))
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer_name: Mapped[str | None] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class IngestionAttempt(Base):
    """The recorded outcome of one attempt to collect reviews for a target."""

    __tablename__ = "ingestion_attempts"
    __table_args__ = (Index("ix_ingestion_attempts_target_id", "target_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("analysis_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reviews_found: Mapped[int] = mapped_column(default=0, nullable=False)
    reviews_skipped: Mapped[int] = mapped_column(default=0, nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
