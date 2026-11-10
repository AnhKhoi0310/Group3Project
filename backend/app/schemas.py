from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

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
        if host not in GOOGLE_HOSTS or (
            host != "maps.google.com" and not parsed.path.startswith("/maps")
        ):
            raise ValueError(URL_WRONG_SITE)
        return value


class TargetRead(BaseModel):
    """Response body. Never includes owner_id."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    source_url: str
    created_at: datetime
