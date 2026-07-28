"""Explicit-cost external verification for the DashScope Qwen profile adapter."""

import asyncio
import os

import pytest

from app.core.config import Settings
from app.infrastructure.qwen_profile import QwenProfileAdapter

pytestmark = pytest.mark.external_integration


def test_qwen_plus_returns_validated_profile_for_controlled_markdown() -> None:
    """Only assert schema facts; never print source Markdown or model output."""
    if os.getenv("RUN_EXTERNAL_INTEGRATION_TESTS") != "true":
        pytest.skip("external Qwen integration tests are disabled")

    settings = Settings()
    assert settings.qwen_api_key is not None
    adapter = QwenProfileAdapter(
        api_key=settings.qwen_api_key.get_secret_value(),
        base_url=settings.qwen_base_url,
        model=settings.qwen_model,
        timeout_seconds=settings.celery_task_soft_time_limit_seconds,
    )

    profile = asyncio.run(
        adapter.extract_profile(
            "## 求职意向\n后端工程师\n\n## 技能\nPython、FastAPI\n\n## 工作经历\n3年后端开发经验"
        )
    )

    assert profile.target_job_titles
