"""Validated application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, Field, PostgresDsn, RedisDsn, SecretStr, model_validator
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


class MineruMcpTransport(StrEnum):
    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"


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
    debug_reset_enabled: bool = False
    log_level: LogLevel = LogLevel.INFO
    database_url: PostgresDsn
    database_pool_size: int = Field(default=5, ge=1, le=20)
    redis_url: RedisDsn
    readiness_timeout_seconds: float = Field(default=2, gt=0, le=10)
    celery_task_time_limit_seconds: int = Field(default=150, ge=1, le=300)
    celery_task_soft_time_limit_seconds: int = Field(default=120, ge=1, le=299)
    celery_task_max_retries: int = Field(default=2, ge=0, le=5)
    celery_retry_backoff_max_seconds: int = Field(default=60, ge=1, le=300)
    celery_execution_lease_seconds: int = Field(default=180, ge=31, le=300)
    celery_dispatch_lease_seconds: int = Field(default=30, ge=5, le=300)
    celery_dispatcher_poll_seconds: int = Field(default=60, ge=5, le=300)
    celery_dispatcher_batch_size: int = Field(default=20, ge=1, le=100)
    object_storage_root: str = Field(default=".careerpass-objects", min_length=1)
    s03_jd_root: str = Field(default="tests/fixtures/job_descriptions", min_length=1)
    mineru_api_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("MINERU_API_KEY", "MINERU_API_TOKEN"),
        repr=False,
    )
    mineru_mcp_url: str | None = Field(default=None, min_length=1)
    mineru_mcp_transport: MineruMcpTransport = MineruMcpTransport.STDIO
    mineru_mcp_command: str = Field(default="uvx", min_length=1, max_length=128)
    mineru_mcp_command_args: tuple[str, ...] = ("mineru-open-mcp",)
    qwen_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
        repr=False,
    )
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        min_length=1,
    )
    qwen_model: str = Field(default="qwen-plus", min_length=1, max_length=128)
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_issuer: str = Field(default="careerpass-api", min_length=1, max_length=128)
    jwt_audience: str = Field(default="careerpass-client", min_length=1, max_length=128)
    jwt_access_token_expire_minutes: int = Field(default=30, ge=8, le=1440)

    @model_validator(mode="after")
    def reject_production_debug(self) -> "Settings":
        if self.app_env is AppEnvironment.PRODUCTION and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV is production")
        if self.app_env is AppEnvironment.PRODUCTION and self.debug_reset_enabled:
            raise ValueError("DEBUG_RESET_ENABLED must be false when APP_ENV is production")
        if self.celery_task_soft_time_limit_seconds >= self.celery_task_time_limit_seconds:
            raise ValueError("CELERY_TASK_SOFT_TIME_LIMIT_SECONDS must be below the hard limit")
        return self

    def require_resume_parsing_credentials(self) -> None:
        """Fail closed when a parsing worker is started without all external credentials."""
        if (
            self.mineru_api_token is None
            or self.qwen_api_key is None
            or not self.mineru_api_token.get_secret_value()
            or not self.qwen_api_key.get_secret_value()
        ):
            raise ValueError("resume parsing credentials are not configured")

    def require_mineru_credentials(self) -> None:
        """Fail closed before starting the MinerU parsing adapter."""
        if self.mineru_api_token is None or not self.mineru_api_token.get_secret_value():
            raise ValueError("MinerU MCP credentials are not configured")
        if self.mineru_mcp_transport is MineruMcpTransport.STREAMABLE_HTTP:
            if self.mineru_mcp_url is None or not self.mineru_mcp_url.startswith(("https://", "http://127.0.0.1/", "http://localhost/")):
                raise ValueError("MinerU MCP endpoint is not configured")


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated settings instance for the process."""
    return Settings()
