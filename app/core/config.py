"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any, Dict, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Media Generation Service"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Asynchronous media generation microservice"

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    RELOAD: bool = Field(default=False, description="Auto-reload on changes")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/media_generation",
        description="Database connection URL",
    )
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend URL"
    )

    # MinIO Configuration
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000", description="MinIO endpoint"
    )
    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin", description="MinIO access key"
    )
    MINIO_SECRET_KEY: str = Field(
        default="minioadmin", description="MinIO secret key"
    )
    MINIO_BUCKET_NAME: str = Field(
        default="media-files", description="MinIO bucket name for media files"
    )
    MINIO_SECURE: bool = Field(default=False, description="Use HTTPS for MinIO")

    # Replicate API Configuration
    REPLICATE_API_TOKEN: Optional[str] = Field(
        default=None, description="Replicate API token"
    )
    REPLICATE_API_URL: str = Field(
        default="https://api.replicate.com/v1", description="Replicate API base URL"
    )

    # Storage Configuration
    STORAGE_TYPE: str = Field(
        default="minio", description="Storage type: 'minio' or 'local'"
    )
    LOCAL_STORAGE_PATH: str = Field(
        default="./media_files", description="Local storage path"
    )

    # Job Configuration
    MAX_RETRY_ATTEMPTS: int = Field(
        default=3, description="Maximum retry attempts for failed jobs"
    )
    RETRY_DELAY_BASE: float = Field(
        default=2.0, description="Base delay for exponential backoff (seconds)"
    )
    JOB_TIMEOUT: int = Field(
        default=300, description="Job timeout in seconds"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    @validator("STORAGE_TYPE")
    def validate_storage_type(cls, v: str) -> str:
        """Validate storage type is supported."""
        if v not in ("minio", "local"):
            raise ValueError("STORAGE_TYPE must be 'minio' or 'local'")
        return v

    @property
    def celery_config(self) -> Dict[str, Any]:
        """Get Celery configuration dictionary."""
        return {
            "broker_url": self.CELERY_BROKER_URL,
            "result_backend": self.CELERY_RESULT_BACKEND,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_time_limit": self.JOB_TIMEOUT,
            "worker_prefetch_multiplier": 1,
            "worker_max_tasks_per_child": 50,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 