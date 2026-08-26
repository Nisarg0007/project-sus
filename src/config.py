"""
Centralized configuration for SUS — Spike Understanding System.

Configuration is loaded from environment variables with sensible defaults.
No secrets or environment-specific values are hardcoded.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "SUS — Spike Understanding System"
    app_version: str = "0.1.0"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # Pipeline defaults
    default_z_threshold: float = 0.5
    default_min_history_days: int = 3
    model_dir: str = "models"

    # Data paths
    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"

    # Database
    database_url: str = "sqlite:///data/sus.db"

    model_config = {"env_prefix": "SUS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
