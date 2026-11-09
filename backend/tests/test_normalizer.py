"""Tests for review normalization."""

import pytest

from app.services.normalizer import (
    ReviewNormalizationError,
    normalize_review,
    normalize_reviews,
)


def test_normalize_review_with_all_fields():
    raw_review = {
        "review_id": "review-123",
        "user": {"name": "Alex"},
        "rating": 4,
        "snippet": "Great service!",
        "date": "2 weeks ago",
    }

    result = normalize_review(raw_review, "place-123")

    assert result == {
        "review_id": "review-123",
        "source": "google_maps",
        "place_id": "place-123",
        "author": "Alex",
        "rating": 4.0,
        "text": "Great service!",
        "date": "2 weeks ago",
    }


def test_normalize_review_with_missing_optional_fields():
    result = normalize_review({}, "place-123")

    assert result["review_id"] is None
    assert result["author"] is None
    assert result["rating"] is None
    assert result["text"] is None
    assert result["date"] is None


@pytest.mark.parametrize("rating", [0, 6, "five", True])
def test_normalize_review_rejects_invalid_rating(rating):
    with pytest.raises(ReviewNormalizationError):
        normalize_review({"rating": rating}, "place-123")


@pytest.mark.parametrize("place_id", ["", "   "])
def test_normalize_review_requires_place_id(place_id):
    with pytest.raises(ReviewNormalizationError):
        normalize_review({"rating": 5}, place_id)


def test_normalize_reviews_multiple_reviews():
    """Normalize all reviews in a batch."""
    raw_reviews = [
        {"review_id": "r1", "rating": 5, "snippet": "Excellent!"},
        {"review_id": "r2", "rating": 3, "snippet": "Average."},
    ]

    results = normalize_reviews(raw_reviews, "place-123")

    assert len(results) == 2
    assert results[0]["rating"] == 5.0
    assert results[1]["text"] == "Average."


def test_normalize_reviews_removes_duplicate_ids():
    """Keep the first occurrence of each review ID."""
    raw_reviews = [
        {"review_id": "r1", "rating": 5},
        {"review_id": "r1", "rating": 1},
        {"review_id": "r2", "rating": 4},
    ]

    results = normalize_reviews(raw_reviews, "place-123")

    assert len(results) == 2
    assert [review["review_id"] for review in results] == ["r1", "r2"]
    assert results[0]["rating"] == 5.0


def test_normalize_reviews_preserves_reviews_without_ids():
    """Do not deduplicate reviews without stable IDs."""
    raw_reviews = [
        {"rating": 5, "snippet": "Good!"},
        {"rating": 5, "snippet": "Good!"},
    ]

    results = normalize_reviews(raw_reviews, "place-123")

    assert len(results) == 2


def test_normalize_reviews_handles_empty_list():
    """An empty batch produces an empty result."""
    assert normalize_reviews([], "place-123") == []


def test_normalize_reviews_rejects_invalid_input():
    """Reject a batch that is not a list."""
    with pytest.raises(ReviewNormalizationError):
        normalize_reviews("not a list", "place-123")


@pytest.mark.parametrize("raw_review", [None, "review", [], 123])
def test_normalize_review_rejects_non_dictionary(raw_review):
    """A review must be a dictionary."""
    with pytest.raises(
        ReviewNormalizationError,
        match="Review must be a dictionary",
    ):
        normalize_review(raw_review, "place-123")


@pytest.mark.parametrize("rating", [-1, 5.5, float("nan"), float("inf")])
def test_normalize_review_rejects_out_of_range_rating(rating):
    """Reject ratings outside the allowed range, including NaN."""
    with pytest.raises(ReviewNormalizationError):
        normalize_review({"rating": rating}, "place-123")


def test_normalize_review_handles_malformed_optional_fields():
    """Unexpected optional field types become None."""
    raw_review = {
        "review_id": 123,
        "user": "not a dictionary",
        "snippet": ["not", "text"],
        "date": 456,
        "rating": 3,
    }

    result = normalize_review(raw_review, "place-123")

    assert result["review_id"] is None
    assert result["author"] is None
    assert result["text"] is None
    assert result["date"] is None
    assert result["rating"] == 3.0


def test_normalize_reviews_rejects_invalid_item():
    """An invalid review inside a batch raises a clear error."""
    raw_reviews = [
        {"review_id": "r1", "rating": 5},
        {"review_id": "r2", "rating": "not a rating"},
    ]

    with pytest.raises(ReviewNormalizationError):
        normalize_reviews(raw_reviews, "place-123")


def test_normalize_review_trims_whitespace():
    """Remove surrounding whitespace from text fields."""
    raw_review = {
        "review_id": "  r123  ",
        "user": {"name": "  Alex  "},
        "snippet": "  Excellent coffee!  ",
        "date": "  2 weeks ago  ",
        "rating": 5,
    }

    result = normalize_review(raw_review, "  place-123  ")

    assert result["review_id"] == "r123"
    assert result["author"] == "Alex"
    assert result["text"] == "Excellent coffee!"
    assert result["date"] == "2 weeks ago"
    assert result["place_id"] == "place-123"


def test_normalize_review_converts_blank_fields_to_none():
    """Blank optional fields become None."""
    raw_review = {
        "review_id": "   ",
        "user": {"name": "   "},
        "snippet": "   ",
        "date": "   ",
    }

    result = normalize_review(raw_review, "place-123")

    assert result["review_id"] is None
    assert result["author"] is None
    assert result["text"] is None
    assert result["date"] is None


def test_normalize_reviews_deduplicates_ids_with_whitespace():
    """Review IDs are cleaned before duplicate detection."""
    raw_reviews = [
        {"review_id": "r1", "rating": 5},
        {"review_id": "  r1  ", "rating": 2},
    ]

    results = normalize_reviews(raw_reviews, "place-123")

    assert len(results) == 1
    assert results[0]["rating"] == 5.0


def test_normalize_review_preserves_internal_whitespace():
    """Keep meaningful formatting inside the review text."""
    raw_review = {
        "snippet": "  Great food!\n\nFriendly staff.  ",
    }

    result = normalize_review(raw_review, "place-123")

    assert result["text"] == "Great food!\n\nFriendly staff."


def test_normalize_review_with_realistic_serpapi_fields():
    """Normalize a review shaped like a SerpApi response."""
    raw_review = {
        "review_id": "review-abc123",
        "user": {
            "name": "Taylor",
            "thumbnail": "https://example.com/avatar.jpg",
        },
        "rating": 4.0,
        "date": "3 months ago",
        "snippet": "Really good coffee and friendly staff.",
        "likes": 2,
    }

    result = normalize_review(raw_review, "ChIJExample123")

    assert result["review_id"] == "review-abc123"
    assert result["author"] == "Taylor"
    assert result["rating"] == 4.0
    assert result["text"] == "Really good coffee and friendly staff."
    assert result["date"] == "3 months ago"
    assert result["source"] == "google_maps"


def test_normalize_review_uses_extracted_snippet_fallback():
    """Use extracted original text if snippet is missing."""
    raw_review = {
        "rating": 5,
        "extracted_snippet": {
            "original": "Excellent service!",
        },
    }

    result = normalize_review(raw_review, "place-123")

    assert result["text"] == "Excellent service!"


def test_normalize_review_handles_malformed_extracted_snippet():
    """Malformed extracted text does not crash normalization."""
    raw_review = {
        "rating": 5,
        "extracted_snippet": "not a dictionary",
    }

    result = normalize_review(raw_review, "place-123")

    assert result["text"] is None


def test_normalize_review_prefers_snippet():
    """Preserve snippet when both text fields exist."""
    raw_review = {
        "snippet": "Preferred text",
        "extracted_snippet": {"original": "Fallback text"},
    }

    result = normalize_review(raw_review, "place-123")

    assert result["text"] == "Preferred text"


@pytest.mark.parametrize("place_id", ["", "   ", None, 123])
def test_normalize_reviews_rejects_invalid_place_id(place_id):
    """Invalid business IDs are rejected even for empty batches."""
    with pytest.raises(
        ReviewNormalizationError,
        match="A business identifier is required",
    ):
        normalize_reviews([], place_id)


@pytest.mark.parametrize("place_id", [None, 123])
def test_normalize_review_rejects_non_string_place_id(place_id):
    """Invalid business ID types produce a normalization error."""
    with pytest.raises(
        ReviewNormalizationError,
        match="A business identifier is required",
    ):
        normalize_review({"rating": 5}, place_id)
