from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "AI Backoffice MVP"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://backoffice:backoffice@localhost:5432/backoffice"

    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    UPLOAD_DIR: str = "/app/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_CURRENCIES: list[str] = ["AED", "USD", "EUR", "GBP"]

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    MAILHOG_API_URL: str = "http://mailhog:8025/api/v2"
    EMAIL_POLL_INTERVAL_SECONDS: int = 15
    INBOUND_EMAIL_DOMAIN: str = "inbound.local"

    RATE_LIMIT: str = "10/minute"


settings = Settings()
