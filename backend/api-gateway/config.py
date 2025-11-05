"""Configuration for API Gateway using pydantic-settings."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """API Gateway settings loaded from environment variables."""

    # Service URLs
    auth_service_url: str = "http://auth-service:8000"
    photos_service_url: str = "http://photos-service:8000"
    blur_detection_service_url: str = "http://blur-detection-service:8000"

    # Redis configuration
    redis_url: str = "redis://redis:6379"

    # HTTP client configuration
    service_timeout: float = 30.0  # seconds
    service_max_retries: int = 3

    # CORS configuration
    cors_origins: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    )

    # Application settings
    app_name: str = "Classify API Gateway"
    app_version: str = "1.0.0"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
