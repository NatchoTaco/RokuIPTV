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
