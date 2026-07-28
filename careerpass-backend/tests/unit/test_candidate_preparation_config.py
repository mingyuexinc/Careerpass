"""Configuration aliases for MinerU MCP and DashScope Qwen credentials."""

import pytest

from app.core.config import MineruMcpTransport, Settings


def test_settings_read_mineru_and_dashscope_standard_environment_names(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("MINERU_API_KEY", "mineru-test-key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-test-key")

    settings = Settings()

    assert settings.mineru_api_token is not None
    assert settings.qwen_api_key is not None
    assert settings.qwen_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.mineru_mcp_transport is MineruMcpTransport.STDIO
    assert settings.mineru_mcp_command == "uvx"
    assert settings.mineru_mcp_command_args == ("mineru-open-mcp",)


def test_empty_resume_parsing_credentials_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("MINERU_API_KEY", "")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")

    with pytest.raises(ValueError, match="resume parsing credentials are not configured"):
        Settings().require_resume_parsing_credentials()
