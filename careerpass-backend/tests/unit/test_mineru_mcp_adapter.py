"""Tests for the controlled MinerU MCP parsing boundary."""

import asyncio
from pathlib import Path

import pytest

from app.infrastructure.mineru_mcp import (
    MineruMcpAdapter,
    MineruTimeoutError,
    MineruUnavailableError,
    MineruUnreadableError,
)


class RecordingTool:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[str] = []

    async def parse_documents(self, *, file_path: str) -> object:
        self.calls.append(file_path)
        return self.result


def test_adapter_uses_system_temporary_pdf_pipeline_and_cleans_it(tmp_path: Path) -> None:
    tool = RecordingTool({"markdown": "# Resume\nTarget role: Engineer"})
    adapter = MineruMcpAdapter(tool=tool, temp_root=tmp_path)

    assert asyncio.run(adapter.extract_markdown(b"%PDF-1.7\nresume")) == "# Resume\nTarget role: Engineer"
    path = tool.calls[0]
    assert Path(path).suffix == ".pdf"
    assert not Path(path).exists()
    assert list(tmp_path.iterdir()) == []


def test_adapter_reads_only_mcp_output_inside_its_temporary_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("sensitive", encoding="utf-8")
    adapter = MineruMcpAdapter(tool=RecordingTool({"markdown_path": str(outside)}), temp_root=tmp_path)

    with pytest.raises(MineruUnreadableError):
        asyncio.run(adapter.extract_markdown(b"%PDF-1.7\nresume"))


def test_adapter_maps_timeout_and_transient_provider_errors() -> None:
    class TimeoutTool:
        async def parse_documents(self, *, file_path: str) -> object:
            del file_path
            raise TimeoutError

    class RateLimitedTool:
        async def parse_documents(self, *, file_path: str) -> object:
            del file_path
            error = RuntimeError()
            error.status_code = 429  # type: ignore[attr-defined]
            raise error

    with pytest.raises(MineruTimeoutError):
        asyncio.run(MineruMcpAdapter(tool=TimeoutTool()).extract_markdown(b"%PDF-1.7\nresume"))
    with pytest.raises(MineruUnavailableError):
        asyncio.run(MineruMcpAdapter(tool=RateLimitedTool()).extract_markdown(b"%PDF-1.7\nresume"))


def test_adapter_rejects_invalid_pdf_and_empty_or_unusable_mcp_output() -> None:
    adapter = MineruMcpAdapter(tool=RecordingTool({"content": []}))

    with pytest.raises(MineruUnreadableError):
        asyncio.run(adapter.extract_markdown(b"not-a-pdf"))
    with pytest.raises(MineruUnreadableError):
        asyncio.run(adapter.extract_markdown(b"%PDF-1.7\nresume"))


def test_adapter_accepts_string_and_text_content_results() -> None:
    string_adapter = MineruMcpAdapter(tool=RecordingTool("# Resume"))
    content_adapter = MineruMcpAdapter(
        tool=RecordingTool({"content": [{"type": "text", "text": "# Resume"}]})
    )

    assert asyncio.run(string_adapter.extract_markdown(b"%PDF-1.7\nresume")) == "# Resume"
    assert asyncio.run(content_adapter.extract_markdown(b"%PDF-1.7\nresume")) == "# Resume"
