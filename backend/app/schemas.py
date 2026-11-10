from datetime import datetime
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)

from app.adapters.review_source import (
    ReviewSourceError,
    extract_data_id,
    extract_place_id,
)

MAX_NAME_LENGTH = 255
MAX_URL_LENGTH = 2048
GOOGLE_HOSTS = {"google.com", "www.google.com", "maps.google.com"}

NAME_REQUIRED = "Enter a name for the business or product you want to analyze."
URL_REQUIRED = "Enter the review page URL."
URL_MALFORMED = (
    "That doesn't look like a valid web address. Include https:// and try again."
)
URL_WRONG_SITE = (
    "This link isn't from Google Maps. "
    "Paste a Google Maps URL for the place you want to analyze."
)
URL_NO_PLACE = (
    "We couldn't find a specific place in that link. Open the business on "
    "Google Maps and copy the full address from your browser's address bar. "
    "Shortened links aren't supported."
)


def _identifies_a_place(url: str) -> bool:
    """True if the ingestion adapter could find a place or data ID in the URL."""
    for extract in (extract_place_id, extract_data_id):
        try:
            extract(url)
            return True
        except ReviewSourceError:
            continue
    return False


class TargetCreate(BaseModel):
    """Request body. Deliberately has no owner_id, user_id or platform."""

    model_config = ConfigDict(extra="ignore")

    name: str
    source_url: str

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(NAME_REQUIRED)
        if len(value) > MAX_NAME_LENGTH:
            raise ValueError(f"Use {MAX_NAME_LENGTH} characters or fewer.")
        return value

    @field_validator("source_url")
    @classmethod
    def check_source_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(URL_REQUIRED)
        if len(value) > MAX_URL_LENGTH:
            raise ValueError(URL_MALFORMED)
        try:
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
        except ValueError:
            raise ValueError(URL_MALFORMED) from None
        if parsed.scheme != "https" or not host:
            raise ValueError(URL_MALFORMED)
        if host not in GOOGLE_HOSTS or not parsed.path.startswith("/maps"):
            raise ValueError(URL_WRONG_SITE)
        if not _identifies_a_place(value):
            raise ValueError(URL_NO_PLACE)
        return value


class TargetUpdate(BaseModel):
    """Partial update body. Ownership and platform are never client-controlled."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    source_url: str | None = None

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Name cannot be null.")

        value = value.strip()
        if not value:
            raise ValueError(NAME_REQUIRED)
        if len(value) > MAX_NAME_LENGTH:
            raise ValueError(f"Use {MAX_NAME_LENGTH} characters or fewer.")
        return value

    @field_validator("source_url")
    @classmethod
    def check_source_url(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Source URL cannot be null.")

        value = value.strip()
        if not value:
            raise ValueError(URL_REQUIRED)
        if len(value) > MAX_URL_LENGTH:
            raise ValueError(URL_MALFORMED)
        try:
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
        except ValueError:
            raise ValueError(URL_MALFORMED) from None
        if parsed.scheme != "https" or not host:
            raise ValueError(URL_MALFORMED)
        if host not in GOOGLE_HOSTS or not parsed.path.startswith("/maps"):
            raise ValueError(URL_WRONG_SITE)
        if not _identifies_a_place(value):
            raise ValueError(URL_NO_PLACE)
        return value

    @model_validator(mode="after")
    def require_at_least_one_change(self):
        if (
            "name" not in self.model_fields_set
            and "source_url" not in self.model_fields_set
        ):
            raise ValueError("Provide at least one field to update.")
        return self


class TargetRead(BaseModel):
    """Response body. Never includes owner_id."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    source_url: str
    created_at: datetime
