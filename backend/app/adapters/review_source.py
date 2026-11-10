"""Retrieve Google Maps customer reviews through SerpApi."""

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.config import get_settings

SERPAPI_URL = "https://serpapi.com/search.json"


class ReviewSourceError(RuntimeError):
    """A safe, categorized review-provider failure."""

    def __init__(
        self,
        category: str,
        message: str,
        status_code: int | None = None,
    ):
        self.category = category
        self.status_code = status_code
        super().__init__(message)


def extract_place_id(source_url: str) -> str:
    """Extract an explicit place ID from a Google Maps URL."""
    try:
        parsed = urlparse(source_url)
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        raise ReviewSourceError(
            "invalid_source",
            "Invalid Google Maps URL.",
        ) from None

    if (
        parsed.scheme != "https"
        or hostname not in {"google.com", "www.google.com", "maps.google.com"}
        or not parsed.path.startswith("/maps")
    ):
        raise ReviewSourceError(
            "invalid_source",
            "A valid Google Maps URL is required.",
        )

    parameters = parse_qs(parsed.query)
    place_ids = parameters.get("query_place_id", [])

    if len(place_ids) != 1 or not place_ids[0].startswith("ChIJ"):
        raise ReviewSourceError(
            "invalid_source",
            "This Google Maps URL needs place identification.",
        )

    return place_ids[0]


def extract_data_id(source_url: str) -> str:
    """Extract a data ID embedded in a Google Maps business URL."""
    try:
        parsed = urlparse(source_url)
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        raise ReviewSourceError(
            "invalid_source",
            "Invalid Google Maps URL.",
        ) from None

    if (
        parsed.scheme != "https"
        or hostname not in {"google.com", "www.google.com", "maps.google.com"}
        or not parsed.path.startswith("/maps/")
    ):
        raise ReviewSourceError(
            "invalid_source",
            "A valid Google Maps URL is required.",
        )

    path = unquote(parsed.path)
    match = re.search(
        r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)(?:!|$)",
        path,
    )

    if not match:
        raise ReviewSourceError(
            "invalid_source",
            "No Google Maps data ID found in URL.",
        )

    return match.group(1)


def extract_business_identifier(source_url: str) -> str:
    """Extract the Google Maps business identifier from a source URL."""
    try:
        return extract_place_id(source_url)
    except ReviewSourceError as exc:
        if exc.category != "invalid_source":
            raise

    return extract_data_id(source_url)


def fetch_reviews(
    place_id: str,
    limit: int = 10,
    *,
    id_type: str = "place_id",
) -> list[dict]:
    """Retrieve up to limit raw reviews, following SerpApi pages."""
    if id_type not in ("place_id", "data_id"):
        raise ValueError("Unsupported Google Maps identifier type.")

    if not place_id or not place_id.strip():
        raise ValueError("A Google Maps place ID is required.")

    if not 1 <= limit <= 50:
        raise ValueError("Review limit must be between 1 and 50.")

    settings = get_settings()

    params = {
        "engine": "google_maps_reviews",
        id_type: place_id,
        "api_key": settings.review_provider_api_key.get_secret_value(),
        "num": min(limit, 20),
        "hl": "en",
    }

    all_reviews = []
    seen_tokens = set()

    with httpx.Client(timeout=30.0) as client:
        while len(all_reviews) < limit:
            try:
                response = client.get(SERPAPI_URL, params=params)
            except httpx.TimeoutException:
                raise ReviewSourceError(
                    "provider_timeout",
                    "Review provider timed out. Please try again.",
                ) from None
            except httpx.RequestError:
                raise ReviewSourceError(
                    "provider_unavailable",
                    "Unable to retrieve customer reviews.",
                ) from None

            if response.status_code == 429:
                raise ReviewSourceError(
                    "provider_quota",
                    "Review provider request limit reached.",
                )

            if response.status_code in (400, 404):
                raise ReviewSourceError(
                    "invalid_source",
                    "Invalid review source or request.",
                )

            if response.status_code in (401, 403) or response.status_code >= 500:
                raise ReviewSourceError(
                    "provider_unavailable",
                    "Unable to retrieve customer reviews.",
                    status_code=response.status_code,
                )

            if response.status_code >= 400:
                raise ReviewSourceError(
                    "unexpected",
                    "Unable to retrieve customer reviews.",
                )

            try:
                data = response.json()
            except ValueError:
                raise ReviewSourceError(
                    "unexpected",
                    "Invalid response from review provider.",
                ) from None

            if not isinstance(data, dict):
                raise ReviewSourceError(
                    "unexpected",
                    "Invalid response from review provider.",
                )

            if data.get("error"):
                raise ReviewSourceError(
                    "unexpected",
                    "Unable to retrieve customer reviews.",
                )

            reviews = data.get("reviews", [])

            if not isinstance(reviews, list):
                raise ReviewSourceError(
                    "unexpected",
                    "Invalid review data received.",
                )

            all_reviews.extend(reviews[: limit - len(all_reviews)])

            pagination = data.get("serpapi_pagination") or {}

            if not isinstance(pagination, dict):
                raise ReviewSourceError(
                    "unexpected",
                    "Invalid pagination data received.",
                )

            next_token = pagination.get("next_page_token")

            # Stop when there is no further page, or an empty page.
            if not next_token or not reviews:
                break

            # Prevent infinite loops if SerpApi repeats a page token.
            if not isinstance(next_token, str) or next_token in seen_tokens:
                raise ReviewSourceError(
                    "unexpected",
                    "Invalid pagination data received.",
                )

            seen_tokens.add(next_token)
            params["next_page_token"] = next_token
            params["num"] = min(limit - len(all_reviews), 20)

    return all_reviews


def fetch_reviews_from_url(source_url: str, limit: int = 10) -> list[dict]:
    """Retrieve reviews using a supported Google Maps business URL."""
    try:
        place_id = extract_place_id(source_url)
    except ReviewSourceError as exc:
        if exc.category != "invalid_source":
            raise
    else:
        return fetch_reviews(place_id, limit=limit)

    data_id = extract_data_id(source_url)
    return fetch_reviews(data_id, limit=limit, id_type="data_id")
