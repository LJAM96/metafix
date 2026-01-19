"""Application configuration using Pydantic settings."""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "MetaFix"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/metafix.db"

    # Security
    secret_key: str = "change-me-in-production"

    # API rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Scan settings
    scan_checkpoint_interval: int = 100
    scan_batch_size: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
