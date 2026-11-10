"""Normalize raw Google Maps reviews into a consistent format."""

import math


class ReviewNormalizationError(ValueError):
    """A raw review contains invalid data."""


def normalize_review(raw_review: dict, place_id: str) -> dict:
    """Convert one SerpApi review into the canonical review structure."""
    if not isinstance(raw_review, dict):
        raise ReviewNormalizationError("Review must be a dictionary.")

    if not isinstance(place_id, str) or not place_id.strip():
        raise ReviewNormalizationError("A business identifier is required.")

    rating = raw_review.get("rating")

    if rating is not None:
        if isinstance(rating, bool) or not isinstance(rating, (int, float)):
            raise ReviewNormalizationError("Review rating must be numeric.")

        if not math.isfinite(rating) or not 1 <= rating <= 5:
            raise ReviewNormalizationError("Review rating must be between 1 and 5.")

        rating = float(rating)

    user = raw_review.get("user")
    if not isinstance(user, dict):
        user = {}

    author = user.get("name")
    author = author.strip() or None if isinstance(author, str) else None

    text = raw_review.get("snippet")
    if not isinstance(text, str) or not text.strip():
        extracted = raw_review.get("extracted_snippet")
        text = extracted.get("original") if isinstance(extracted, dict) else None

    text = text.strip() or None if isinstance(text, str) else None

    date = raw_review.get("date")
    date = date.strip() or None if isinstance(date, str) else None

    review_id = raw_review.get("review_id")
    review_id = review_id.strip() or None if isinstance(review_id, str) else None

    return {
        "review_id": review_id,
        "source": "google_maps",
        "place_id": place_id.strip(),
        "author": author,
        "rating": rating,
        "text": text,
        "date": date,
    }


def normalize_reviews_with_skips(
    raw_reviews: list,
    place_id: str,
) -> tuple[list[dict], int]:
    """Normalize a batch, skipping malformed, incomplete, and duplicate records.

    A usable canonical review must have non-empty text and a rating from 1 to 5.
    The returned integer counts every skipped record.
    """
    if not isinstance(raw_reviews, list):
        raise ReviewNormalizationError("Reviews must be a list.")

    if not isinstance(place_id, str) or not place_id.strip():
        raise ReviewNormalizationError("A business identifier is required.")

    normalized_reviews = []
    seen_review_ids = set()
    skipped = 0

    for raw_review in raw_reviews:
        try:
            normalized = normalize_review(raw_review, place_id)
        except ReviewNormalizationError:
            skipped += 1
            continue

        if not normalized["text"] or normalized["rating"] is None:
            skipped += 1
            continue

        review_id = normalized["review_id"]
        if review_id is not None:
            if review_id in seen_review_ids:
                skipped += 1
                continue
            seen_review_ids.add(review_id)

        normalized_reviews.append(normalized)

    return normalized_reviews, skipped


def normalize_reviews(raw_reviews: list, place_id: str) -> list[dict]:
    """Compatibility wrapper returning only usable normalized reviews."""
    normalized, _skipped = normalize_reviews_with_skips(raw_reviews, place_id)
    return normalized
