import pytest

from app.services.ingestion import (
    IngestionError,
    collect_reviews,
)

PLACE_ID_URL = (
    "https://www.google.com/maps/search/"
    "?api=1&query=Coffee&query_place_id=ChIJExample123"
)

DATA_ID_URL = (
    "https://www.google.com/maps/place/Example+Cafe/"
    "data=!4m5!3m4!1s0x123abc:0x456def!8m2"
)


def test_collect_reviews_uses_google_place_id():
    raw_reviews = [
        {
            "review_id": "r1",
            "rating": 5,
            "snippet": "Excellent coffee!",
        }
    ]

    outcome = collect_reviews(
        PLACE_ID_URL,
        lambda _url: raw_reviews,
    )

    assert outcome.reviews_found == 1
    assert outcome.reviews[0]["place_id"] == "ChIJExample123"


def test_collect_reviews_uses_google_data_id():
    raw_reviews = [
        {
            "review_id": "r1",
            "rating": 4,
            "snippet": "Good coffee!",
        }
    ]

    outcome = collect_reviews(
        DATA_ID_URL,
        lambda _url: raw_reviews,
    )

    assert outcome.reviews_found == 1
    assert outcome.reviews[0]["place_id"] == "0x123abc:0x456def"


def test_collect_reviews_skips_invalid_records():
    raw_reviews = [
        {
            "review_id": "r1",
            "rating": 5,
            "snippet": "Excellent!",
        },
        {
            "review_id": "r2",
            "rating": 9,
            "snippet": "Invalid rating",
        },
        {
            "review_id": "r3",
            "rating": 4,
        },
    ]

    outcome = collect_reviews(
        PLACE_ID_URL,
        lambda _url: raw_reviews,
    )

    assert outcome.reviews_found == 1
    assert outcome.reviews_skipped == 2


def test_collect_reviews_rejects_invalid_source_before_fetch():
    fetch_called = False

    def fake_fetch(_url):
        nonlocal fetch_called
        fetch_called = True
        return []

    with pytest.raises(IngestionError) as caught:
        collect_reviews(
            "https://example.com/not-a-google-maps-url",
            fake_fetch,
        )

    assert caught.value.category == "invalid_source"
    assert fetch_called is False
