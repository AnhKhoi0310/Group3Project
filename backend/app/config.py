"""Application configuration, loaded from the environment or backend/.env.

Run ``python -m app.config`` from backend/ to check the current configuration.
"""

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class ConfigurationError(RuntimeError):
    """Required configuration is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: SecretStr = Field(min_length=1)
    firebase_project_id: str = Field(min_length=1)
    firebase_credentials_path: str = Field(min_length=1)
    review_provider_api_key: SecretStr = Field(min_length=1)
    ingestion_max_reviews: int = Field(default=50, gt=0)

    @property
    def firebase_credentials_file(self) -> Path:
        """Absolute key file path; relative values are from the backend folder."""
        return ENV_FILE.parent / self.firebase_credentials_path


class CorsSettings(BaseSettings):
    """Separate from Settings because middleware is registered at import time."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


def load_settings(**overrides) -> Settings:
    """Build Settings, reporting problems by variable name only.

    Pydantic's own error text includes the rejected input, which could be a
    secret, so the original exception is deliberately not chained.
    """
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        names = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        message = (
            "ReviewLens cannot start: missing or invalid configuration: "
            f"{', '.join(names)}. "
            "Set these in backend/.env (see backend/.env.example) "
            "or as environment variables."
        )
    raise ConfigurationError(message) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()


if __name__ == "__main__":
    try:
        get_settings()
    except ConfigurationError as exc:
        sys.exit(str(exc))
    print("Configuration OK.")
