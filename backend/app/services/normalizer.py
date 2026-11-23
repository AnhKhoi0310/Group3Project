"""Normalize raw Google Maps reviews into a consistent format."""

import math
from urllib.parse import urlparse

MAX_REVIEW_IMAGES = 6
MAX_IMAGE_URL_LENGTH = 1024
# Review photos and reviewer avatars are served by Google's image CDN. Other
# hosts are dropped, so provider data can't point the browser anywhere else.
ALLOWED_IMAGE_HOSTS = ("googleusercontent.com", "ggpht.com")


class ReviewNormalizationError(ValueError):
    """A raw review contains invalid data."""


def image_url(value: object) -> str | None:
    """Return a safe https image URL from Google's image hosts, or None."""
    if isinstance(value, dict):
        value = value.get("image") or value.get("thumbnail")
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > MAX_IMAGE_URL_LENGTH:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    allowed = any(host == h or host.endswith(f".{h}") for h in ALLOWED_IMAGE_HOSTS)
    return value if parsed.scheme == "https" and allowed else None


def _image_urls(raw_images: object) -> list[str]:
    if not isinstance(raw_images, list):
        return []
    urls: list[str] = []
    for item in raw_images:
        url = image_url(item)
        if url and url not in urls:
            urls.append(url)
        if len(urls) == MAX_REVIEW_IMAGES:
            break
    return urls


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
        "avatar_url": image_url(user.get("thumbnail")),
        "image_urls": _image_urls(raw_review.get("images")),
    }


def normalize_reviews_detailed(
    raw_reviews: list,
    place_id: str,
) -> tuple[list[dict], int, dict[str, int]]:
    """Normalize a batch, counting skipped records and grouping them by reason.

    A usable canonical review must have non-empty text and a rating from 1 to 5.
    """
    if not isinstance(raw_reviews, list):
        raise ReviewNormalizationError("Reviews must be a list.")

    if not isinstance(place_id, str) or not place_id.strip():
        raise ReviewNormalizationError("A business identifier is required.")

    normalized_reviews = []
    seen_review_ids = set()
    skipped = 0
    skipped_reasons: dict[str, int] = {}

    def record_skip(reason: str) -> None:
        nonlocal skipped
        skipped += 1
        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

    for raw_review in raw_reviews:
        if not isinstance(raw_review, dict):
            record_skip("malformed_record")
            continue

        try:
            normalized = normalize_review(raw_review, place_id)
        except ReviewNormalizationError:
            record_skip("invalid_rating")
            continue

        if normalized["rating"] is None:
            record_skip("invalid_rating")
            continue

        if not normalized["text"]:
            record_skip("missing_text")
            continue

        review_id = normalized["review_id"]
        if review_id is not None:
            if review_id in seen_review_ids:
                record_skip("duplicate_record")
                continue
            seen_review_ids.add(review_id)

        normalized_reviews.append(normalized)

    return normalized_reviews, skipped, skipped_reasons


def normalize_reviews_with_skips(
    raw_reviews: list,
    place_id: str,
) -> tuple[list[dict], int]:
    """Normalize a batch, skipping malformed, incomplete, and duplicate records.

    A usable canonical review must have non-empty text and a rating from 1 to 5.
    The returned integer counts every skipped record.
    """
    normalized, skipped, _reasons = normalize_reviews_detailed(
        raw_reviews,
        place_id,
    )
    return normalized, skipped


def normalize_reviews(raw_reviews: list, place_id: str) -> list[dict]:
    """Compatibility wrapper returning only usable normalized reviews."""
    normalized, _skipped = normalize_reviews_with_skips(raw_reviews, place_id)
    return normalized
