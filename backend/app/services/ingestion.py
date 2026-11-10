"""Collect and normalize reviews for one target.

Persistence and run state are later stories (S1-022, S1-023).
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.adapters.review_source import ReviewSourceError
from app.services.normalizer import ReviewNormalizationError, normalize_reviews


@dataclass(frozen=True)
class IngestionOutcome:
    reviews_found: int
    reviews_skipped: int


class IngestionError(Exception):
    """Ingestion failed. The category is one of the documented failure categories."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def collect_reviews(
    target_id: int,
    source_url: str,
    fetch: Callable[[str], list[dict]],
) -> IngestionOutcome:
    """Fetch reviews from the target's own source URL and normalize them."""
    if not source_url or not source_url.strip():
        raise IngestionError("invalid_source")

    try:
        raw_reviews = fetch(source_url)
    except ReviewSourceError as exc:
        raise IngestionError(exc.category) from exc
    except ValueError as exc:
        raise IngestionError("unexpected") from exc

    try:
        normalized = normalize_reviews(raw_reviews, str(target_id))
    except ReviewNormalizationError as exc:
        raise IngestionError("unexpected") from exc

    usable = [r for r in normalized if r["text"] and r["rating"] is not None]
    return IngestionOutcome(
        reviews_found=len(usable),
        reviews_skipped=len(normalized) - len(usable),
    )
