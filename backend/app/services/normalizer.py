"""Normalize raw Google Maps reviews into a consistent format."""


class ReviewNormalizationError(ValueError):
    """A raw review contains invalid data."""


def normalize_review(
    raw_review: dict,
    place_id: str,
) -> dict:
    """Convert a SerpApi review into a consistent review dictionary."""
    if not isinstance(raw_review, dict):
        raise ReviewNormalizationError("Review must be a dictionary.")

    if not isinstance(place_id, str) or not place_id.strip():
        raise ReviewNormalizationError("A business identifier is required.")

    rating = raw_review.get("rating")

    if rating is not None:
        if isinstance(rating, bool) or not isinstance(rating, (int, float)):
            raise ReviewNormalizationError("Review rating must be numeric.")

        if not 1 <= rating <= 5:
            raise ReviewNormalizationError("Review rating must be between 1 and 5.")

        rating = float(rating)

    user = raw_review.get("user") or {}
    if not isinstance(user, dict):
        user = {}

    author = user.get("name")
    if isinstance(author, str):
        author = author.strip() or None
    else:
        author = None

    text = raw_review.get("snippet")
    if not isinstance(text, str) or not text.strip():
        extracted = raw_review.get("extracted_snippet")
        if isinstance(extracted, dict):
            text = extracted.get("original")

    if isinstance(text, str):
        text = text.strip() or None
    else:
        text = None

    date = raw_review.get("date")
    if isinstance(date, str):
        date = date.strip() or None
    else:
        date = None

    review_id = raw_review.get("review_id")
    if isinstance(review_id, str):
        review_id = review_id.strip() or None
    else:
        review_id = None

    return {
        "review_id": review_id,
        "source": "google_maps",
        "place_id": place_id.strip(),
        "author": author,
        "rating": rating,
        "text": text,
        "date": date,
    }


def normalize_reviews(
    raw_reviews: list[dict],
    place_id: str,
) -> list[dict]:
    """Normalize a batch of reviews and remove duplicate review IDs."""
    if not isinstance(raw_reviews, list):
        raise ReviewNormalizationError("Reviews must be a list.")

    if not isinstance(place_id, str) or not place_id.strip():
        raise ReviewNormalizationError("A business identifier is required.")

    normalized_reviews = []
    seen_review_ids = set()

    for raw_review in raw_reviews:
        normalized = normalize_review(raw_review, place_id)

        review_id = normalized["review_id"]

        if review_id is not None:
            if review_id in seen_review_ids:
                continue

            seen_review_ids.add(review_id)

        normalized_reviews.append(normalized)

    return normalized_reviews
