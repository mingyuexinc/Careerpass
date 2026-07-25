"""Validated application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Permitted application log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Settings available in L1; external-service settings belong to later layers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="CareerPass API", min_length=1)
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    database_url: PostgresDsn
    database_pool_size: int = Field(default=5, ge=1, le=20)
    redis_url: RedisDsn
    readiness_timeout_seconds: float = Field(default=2, gt=0, le=10)
    celery_task_time_limit_seconds: int = Field(default=30, ge=1, le=300)
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_requests: int = Field(default=10, ge=1, le=1000)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    auth_rate_limit_timeout_seconds: float = Field(default=0.2, gt=0, le=5)
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_issuer: str = Field(default="careerpass-api", min_length=1, max_length=128)
    jwt_audience: str = Field(default="careerpass-client", min_length=1, max_length=128)
    jwt_access_token_expire_minutes: int = Field(default=30, ge=8, le=1440)

    @model_validator(mode="after")
    def reject_production_debug(self) -> "Settings":
        if self.app_env is AppEnvironment.PRODUCTION and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV is production")
        if self.app_env is AppEnvironment.PRODUCTION and not self.auth_rate_limit_enabled:
            raise ValueError("AUTH_RATE_LIMIT_ENABLED must be true when APP_ENV is production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated settings instance for the process."""
    return Settings()
