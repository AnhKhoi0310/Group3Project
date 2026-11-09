"""Tests for SerpApi review extraction."""

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from pydantic import SecretStr

from app.adapters import review_source


@pytest.fixture
def fake_settings(monkeypatch):
    """Use a fake API key instead of the real SerpApi key."""
    settings = SimpleNamespace(review_provider_api_key=SecretStr("test-key"))
    monkeypatch.setattr(review_source, "get_settings", lambda: settings)


def test_fetch_reviews_success(fake_settings):
    """Valid provider responses return review records."""
    reviews = [
        {"snippet": "Great food!", "rating": 5},
        {"snippet": "Slow service.", "rating": 2},
    ]

    response = httpx.Response(
        200,
        json={"reviews": reviews},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = response

        result = review_source.fetch_reviews("test-place-id", limit=2)

    assert result == reviews


@pytest.mark.parametrize("place_id", ["", "   "])
def test_fetch_reviews_rejects_missing_place_id(place_id):
    """Missing place IDs are rejected before contacting SerpApi."""
    with pytest.raises(ValueError, match="place ID"):
        review_source.fetch_reviews(place_id)


def test_fetch_reviews_handles_timeout(fake_settings):
    """A provider timeout produces a safe error."""
    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = (
            httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(
            review_source.ReviewSourceError,
            match="Review provider timed out",
        ):
            review_source.fetch_reviews("test-place-id")


def test_fetch_reviews_handles_provider_error(fake_settings):
    """Provider API errors do not expose internal details."""
    response = httpx.Response(
        200,
        json={"error": "Invalid API key: secret-provider-details"},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = response

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id")

    assert "secret-provider-details" not in str(caught.value)


@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (400, "invalid_source"),
        (404, "invalid_source"),
        (429, "provider_quota"),
        (401, "provider_unavailable"),
        (403, "provider_unavailable"),
        (500, "provider_unavailable"),
        (503, "provider_unavailable"),
    ],
)
def test_fetch_reviews_categorizes_http_errors(fake_settings, status_code, category):
    """HTTP failures produce the correct safe category."""
    response = httpx.Response(
        status_code,
        json={"error": "secret-provider-details"},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = response

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id")

    assert caught.value.category == category
    assert "secret-provider-details" not in str(caught.value)


def test_fetch_reviews_categorizes_timeout(fake_settings):
    """Timeouts receive a distinct failure category."""
    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = (
            httpx.TimeoutException("Timed out")
        )

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id")

    assert caught.value.category == "provider_timeout"


def test_fetch_reviews_categorizes_connection_error(fake_settings):
    """Connection failures are reported safely."""
    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = (
            httpx.ConnectError("Connection failed")
        )

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id")

    assert caught.value.category == "provider_unavailable"


def test_fetch_reviews_rejects_invalid_json(fake_settings):
    """Malformed provider responses are not accepted."""
    response = httpx.Response(
        200,
        content="not valid JSON",
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = response

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id")

    assert caught.value.category == "unexpected"


def test_fetch_reviews_combines_multiple_pages(fake_settings):
    """Reviews from multiple pages are combined."""
    first_page = httpx.Response(
        200,
        json={
            "reviews": [{"snippet": "First review", "rating": 5}],
            "serpapi_pagination": {"next_page_token": "page-two"},
        },
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )
    second_page = httpx.Response(
        200,
        json={
            "reviews": [{"snippet": "Second review", "rating": 4}],
        },
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.side_effect = [first_page, second_page]

        reviews = review_source.fetch_reviews("test-place-id", limit=3)

    assert len(reviews) == 2
    assert reviews[0]["snippet"] == "First review"
    assert reviews[1]["snippet"] == "Second review"
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1].kwargs["params"]["next_page_token"] == "page-two"


def test_fetch_reviews_stops_at_limit(fake_settings):
    """Only the requested number of reviews is returned."""
    response = httpx.Response(
        200,
        json={
            "reviews": [
                {"snippet": "Review 1", "rating": 5},
                {"snippet": "Review 2", "rating": 4},
                {"snippet": "Review 3", "rating": 3},
            ],
            "serpapi_pagination": {"next_page_token": "unused-token"},
        },
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.return_value = response

        reviews = review_source.fetch_reviews("test-place-id", limit=2)

    assert len(reviews) == 2
    assert mock_get.call_count == 1


def test_fetch_reviews_rejects_repeated_page_token(fake_settings):
    """Repeated page tokens cannot cause infinite requests."""
    response = httpx.Response(
        200,
        json={
            "reviews": [{"snippet": "Review", "rating": 5}],
            "serpapi_pagination": {"next_page_token": "same-token"},
        },
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.return_value = response

        with pytest.raises(review_source.ReviewSourceError) as caught:
            review_source.fetch_reviews("test-place-id", limit=5)

    assert caught.value.category == "unexpected"
    assert mock_get.call_count == 2


def test_fetch_reviews_caps_each_request_at_20(fake_settings):
    """Individual API requests never exceed 20 reviews."""
    response = httpx.Response(
        200,
        json={"reviews": []},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.return_value = response

        review_source.fetch_reviews("test-place-id", limit=50)

    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs["params"]["num"] == 20


def test_extract_place_id_from_google_maps_url():
    """Extract an explicitly provided Google Maps place ID."""
    url = (
        "https://www.google.com/maps/search/"
        "?api=1&query=Coffee&query_place_id=ChIJExample123"
    )

    assert review_source.extract_place_id(url) == "ChIJExample123"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/maps/search/?query_place_id=ChIJExample123",
        "https://google.com.evil.example/maps/search/?query_place_id=ChIJExample123",
        "http://www.google.com/maps/search/?query_place_id=ChIJExample123",
        "not-a-url",
        "",
    ],
)
def test_extract_place_id_rejects_invalid_urls(url):
    """Reject invalid or untrusted Google Maps URLs."""
    with pytest.raises(review_source.ReviewSourceError) as caught:
        review_source.extract_place_id(url)

    assert caught.value.category == "invalid_source"


def test_extract_place_id_rejects_url_without_explicit_id():
    """Do not guess the business from an ordinary Maps URL."""
    url = "https://www.google.com/maps/place/Example+Coffee"

    with pytest.raises(review_source.ReviewSourceError) as caught:
        review_source.extract_place_id(url)

    assert caught.value.category == "invalid_source"


def test_extract_data_id_from_google_maps_url():
    """Extract a data ID from a Google Maps business URL."""
    url = (
        "https://www.google.com/maps/place/Example+Cafe/"
        "data=!4m5!3m4!1s0x123abc:0x456def!8m2"
    )

    assert review_source.extract_data_id(url) == "0x123abc:0x456def"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/maps/place/Test/data=!1s0x123:0x456!",
        "https://google.com.evil.example/maps/place/Test/data=!1s0x123:0x456!",
        "https://www.google.com/maps/place/Example+Cafe",
        "https://www.google.com/maps/place/Test/data=!1snot-a-data-id!",
        "not-a-url",
    ],
)
def test_extract_data_id_rejects_invalid_urls(url):
    """Reject untrusted URLs and URLs without a valid data ID."""
    with pytest.raises(review_source.ReviewSourceError) as caught:
        review_source.extract_data_id(url)

    assert caught.value.category == "invalid_source"


def test_fetch_reviews_from_url_uses_place_id():
    """URLs containing place IDs use the correct identifier."""
    url = (
        "https://www.google.com/maps/search/"
        "?api=1&query=Coffee&query_place_id=ChIJExample123"
    )

    with patch.object(review_source, "fetch_reviews") as mock_fetch:
        mock_fetch.return_value = [{"snippet": "Great!"}]

        reviews = review_source.fetch_reviews_from_url(url, limit=5)

    mock_fetch.assert_called_once_with("ChIJExample123", limit=5)
    assert len(reviews) == 1


def test_fetch_reviews_from_url_uses_data_id():
    """URLs containing data IDs use the correct identifier type."""
    url = (
        "https://www.google.com/maps/place/Example+Cafe/"
        "data=!4m5!3m4!1s0x123abc:0x456def!8m2"
    )

    with patch.object(review_source, "fetch_reviews") as mock_fetch:
        mock_fetch.return_value = [{"snippet": "Great!"}]

        reviews = review_source.fetch_reviews_from_url(url, limit=5)

    mock_fetch.assert_called_once_with(
        "0x123abc:0x456def",
        limit=5,
        id_type="data_id",
    )
    assert len(reviews) == 1


def test_fetch_reviews_sends_data_id_to_serpapi(fake_settings):
    """Data IDs use the data_id parameter, not place_id."""
    response = httpx.Response(
        200,
        json={"reviews": [{"snippet": "Great food!", "rating": 5}]},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.return_value = response

        reviews = review_source.fetch_reviews(
            "0x123abc:0x456def",
            limit=5,
            id_type="data_id",
        )

    params = mock_get.call_args.kwargs["params"]

    assert params["engine"] == "google_maps_reviews"
    assert params["data_id"] == "0x123abc:0x456def"
    assert "place_id" not in params
    assert params["num"] == 5
    assert len(reviews) == 1


def test_fetch_reviews_rejects_unsupported_identifier(fake_settings):
    """Unknown identifier types are rejected before API calls."""
    with patch.object(review_source.httpx, "Client") as mock_client:
        with pytest.raises(
            ValueError,
            match="Unsupported Google Maps identifier type",
        ):
            review_source.fetch_reviews(
                "example-id",
                id_type="unknown",
            )

    mock_client.assert_not_called()


@pytest.mark.parametrize(
    ("url", "expected_key", "expected_id"),
    [
        (
            "https://www.google.com/maps/search/"
            "?api=1&query=Cafe&query_place_id=ChIJExample123",
            "place_id",
            "ChIJExample123",
        ),
        (
            "https://www.google.com/maps/place/Example+Cafe/"
            "data=!4m5!3m4!1s0x123abc:0x456def!8m2",
            "data_id",
            "0x123abc:0x456def",
        ),
    ],
)
def test_url_to_serpapi_request(fake_settings, url, expected_key, expected_id):
    """A Google Maps URL produces the correct API request."""
    response = httpx.Response(
        200,
        json={"reviews": [{"snippet": "Great food!", "rating": 5}]},
        request=httpx.Request("GET", "https://serpapi.com/search.json"),
    )

    with patch.object(review_source.httpx, "Client") as mock_client:
        mock_get = mock_client.return_value.__enter__.return_value.get
        mock_get.return_value = response

        reviews = review_source.fetch_reviews_from_url(url, limit=5)

    params = mock_get.call_args.kwargs["params"]

    assert params["engine"] == "google_maps_reviews"
    assert params[expected_key] == expected_id
    assert len(reviews) == 1
    assert mock_get.call_count == 1
