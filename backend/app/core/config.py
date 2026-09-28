"""Application configuration module using pydantic-settings."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Root directory of the monorepo
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    PROJECT_NAME: str = "Hilly-Region Flash Flood & Landslide EWS"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database configuration: SQLite default for offline/local, PostgreSQL for PostGIS
    DATABASE_URL: str = "sqlite:///./data/ews.db"

    # Redis cache & message broker
    REDIS_URL: str = "redis://localhost:6379/0"

    # Pilot District Defaults
    DEFAULT_DISTRICT: str = "Uttarkashi"
    DEFAULT_STATE: str = "Uttarakhand"

    # Escalation Ladder Timeout (5 minutes default)
    ALERT_ESCALATION_TIMEOUT_SECONDS: int = 300

    @property
    def is_postgres(self) -> bool:
        """Return True if DATABASE_URL targets PostgreSQL/PostGIS."""
        return self.DATABASE_URL.startswith("postgresql") or self.DATABASE_URL.startswith("postgres")

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
