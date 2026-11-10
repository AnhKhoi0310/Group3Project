"""Collect and normalize reviews for one analysis target."""

from collections.abc import Callable
from dataclasses import dataclass

from app.adapters.review_source import ReviewSourceError
from app.services.normalizer import (
    ReviewNormalizationError,
    normalize_reviews_with_skips,
)


@dataclass(frozen=True)
class IngestionOutcome:
    reviews: list[dict]
    reviews_found: int
    reviews_skipped: int


class IngestionError(Exception):
    """Ingestion failed. The category is safe to record and report."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def collect_reviews(
    target_id: int,
    source_url: str,
    fetch: Callable[[str], list[dict]],
) -> IngestionOutcome:
    """Fetch from the target's stored URL and return only usable reviews."""
    if not source_url or not source_url.strip():
        raise IngestionError("invalid_source")

    try:
        raw_reviews = fetch(source_url)
    except ReviewSourceError as exc:
        raise IngestionError(exc.category) from exc
    except Exception as exc:
        raise IngestionError("unexpected") from exc

    try:
        reviews, skipped = normalize_reviews_with_skips(
            raw_reviews,
            str(target_id),
        )
    except ReviewNormalizationError as exc:
        raise IngestionError("unexpected") from exc

    # An empty provider response is valid, but a non-empty response
    # containing no usable reviews indicates malformed provider data.
    if raw_reviews and not reviews:
        raise IngestionError("unexpected")

    return IngestionOutcome(
        reviews=reviews,
        reviews_found=len(reviews),
        reviews_skipped=skipped,
    )
