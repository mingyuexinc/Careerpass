"""Explicit-cost external verification for the official MinerU stdio Bridge."""

import asyncio
import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.infrastructure.mineru_mcp import MineruMcpAdapter
from app.infrastructure.mineru_mcp_client import MineruStdioClient

pytestmark = pytest.mark.external_integration


def test_controlled_resume_is_parsed_by_mineru_stdio_bridge(tmp_path: Path) -> None:
    """Verify only non-sensitive success facts; never print source or extracted content."""
    if os.getenv("RUN_EXTERNAL_INTEGRATION_TESTS") != "true":
        pytest.skip("external MinerU integration tests are disabled")

    settings = Settings()
    settings.require_mineru_credentials()
    assert settings.mineru_api_token is not None
    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "candidate_preparation"
        / "resumes"
        / "resume_01.pdf"
    )
    client = MineruStdioClient(
        command=settings.mineru_mcp_command,
        command_args=settings.mineru_mcp_command_args,
        api_token=settings.mineru_api_token.get_secret_value(),
        timeout_seconds=settings.celery_task_soft_time_limit_seconds,
    )
    adapter = MineruMcpAdapter(tool=client, temp_root=tmp_path)

    markdown = asyncio.run(adapter.extract_markdown(fixture.read_bytes()))

    assert markdown.strip()
    assert list(tmp_path.iterdir()) == []
