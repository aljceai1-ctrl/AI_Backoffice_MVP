"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration.

    All values can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql://backoffice:backoffice@localhost:5432/backoffice"
    TEST_DATABASE_URL: str = (
        "postgresql://backoffice:backoffice@localhost:5433/backoffice_test"
    )

    # Security
    BACKOFFICE_API_KEY: str = "dev-api-key-change-me"

    # Storage
    UPLOAD_DIR: str = "./data/uploads"

    # Business rules
    ALLOWED_CURRENCIES: list[str] = ["AED", "USD", "EUR"]

    # Observability
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()
