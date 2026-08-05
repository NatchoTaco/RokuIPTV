from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StreamForge"
    env: str = "development"
    version: str = "0.1.0"
    secret_key: str = "change-this-development-secret"
    database_url: str = "postgresql+psycopg://streamforge:streamforge@localhost:5432/streamforge"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    cookie_name: str = "streamforge_session"
    cookie_secure: bool = False
    session_ttl_minutes: int = Field(default=10080, ge=5)
    log_level: str = "INFO"
    source_upload_dir: str = "/app/data/uploads"
    source_request_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    source_max_playlist_bytes: int = Field(default=20_000_000, ge=1024)
    source_worker_poll_seconds: float = Field(default=2.0, ge=0.5, le=60.0)
<<<<<<< HEAD
=======
    source_large_playlist_warning_entries: int = Field(default=100_000, ge=1)
    source_import_confirmation_threshold_entries: int = Field(default=50_000, ge=1)
    source_import_batch_size: int = Field(default=1_000, ge=1, le=10_000)
    source_estimated_entries_per_second: int = Field(default=250, ge=1)
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
    allow_private_source_urls: bool = False

    model_config = SettingsConfigDict(
        env_prefix="STREAMFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    def validate_runtime(self) -> None:
        if self.is_production and self.secret_key == "change-this-development-secret":
            msg = "STREAMFORGE_SECRET_KEY must be changed in production"
            raise RuntimeError(msg)


@lru_cache
def get_settings() -> Settings:
    return Settings()
