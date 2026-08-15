"""Controlled MinerU MCP adapter for one temporary formal-resume PDF."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class MineruMcpError(Exception):
    """Base class for safe, classified MinerU adapter failures."""

    failure_code: str
    retryable: bool


class MineruTimeoutError(MineruMcpError):
    failure_code = "parser_timeout"
    retryable = True


class MineruUnavailableError(MineruMcpError):
    failure_code = "internal_error"
    retryable = True

    def __init__(self, *, diagnostic_stage: str = "unknown", diagnostic_kind: str = "unknown"):
        super().__init__()
        self.diagnostic_stage = diagnostic_stage
        self.diagnostic_kind = diagnostic_kind


class MineruUnreadableError(MineruMcpError):
    failure_code = "file_unreadable"
    retryable = False


class MineruMcpTool(Protocol):
    """The narrow official `parse_documents` MCP tool contract used by this service."""

    async def parse_documents(self, *, file_path: str) -> object: ...


class MineruMcpAdapter:
    """Pass a system-created PDF path to MCP and return only non-empty Markdown in memory."""

    def __init__(self, *, tool: MineruMcpTool, temp_root: Path | None = None) -> None:
        self._tool = tool
        self._temp_root = temp_root

    async def extract_markdown(self, pdf_content: bytes) -> str:
        """Extract Markdown with pipeline mode and remove every temporary artifact on exit."""
        if not pdf_content.startswith(b"%PDF-"):
            raise MineruUnreadableError
        with tempfile.TemporaryDirectory(prefix="careerpass-mineru-", dir=self._temp_root) as directory:
            root = Path(directory).resolve()
            pdf_path = root / f"{uuid4().hex}.pdf"
            pdf_path.write_bytes(pdf_content)
            try:
                result = await self._tool.parse_documents(file_path=str(pdf_path))
            except TimeoutError as exc:
                raise MineruTimeoutError from exc
            except Exception as exc:
                raise _classify_tool_error(exc) from None
            markdown = _extract_markdown(result, root)
        if not markdown.strip():
            raise MineruUnreadableError
        return markdown


def _extract_markdown(result: object, root: Path) -> str:
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, Mapping):
            return _extract_markdown(parsed, root)
        if result.strip().lower().startswith("parsing complete!"):
            raise MineruUnreadableError
        return result
    if not isinstance(result, Mapping):
        raise MineruUnreadableError
    results = result.get("results")
    if isinstance(results, list):
        if len(results) != 1 or not isinstance(results[0], Mapping):
            _raise_result_error(results)
        entry = results[0]
        if entry.get("status") != "success":
            _raise_result_error(results)
        return _extract_result_entry(entry, root)
    if result.get("status") in {"error", "partial_success"}:
        _raise_result_error([result])
    markdown = result.get("markdown")
    if isinstance(markdown, str):
        return markdown
    markdown_path = result.get("markdown_path")
    if isinstance(markdown_path, str):
        candidate = Path(markdown_path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        raise MineruUnreadableError
    content = result.get("content")
    if isinstance(content, list):
        text_blocks = [
            item.get("text")
            for item in content
            if isinstance(item, Mapping) and item.get("type") == "text" and isinstance(item.get("text"), str)
        ]
        if text_blocks:
            joined = "\n".join(text_blocks)
            return _extract_markdown(joined, root)
    raise MineruUnreadableError


def _extract_result_entry(entry: Mapping[object, object], root: Path) -> str:
    if entry.get("truncated") is True:
        path = entry.get("extract_path")
        if isinstance(path, str):
            return _read_controlled_markdown(path, root)
        raise MineruUnreadableError
    content = entry.get("content")
    if isinstance(content, str) and content.strip():
        return content
    path = entry.get("extract_path")
    if isinstance(path, str):
        return _read_controlled_markdown(path, root)
    raise MineruUnreadableError


def _read_controlled_markdown(path: str, root: Path) -> str:
    candidate = Path(path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise MineruUnreadableError
    markdown = candidate.read_text(encoding="utf-8")
    if not markdown.strip():
        raise MineruUnreadableError
    return markdown


def _raise_result_error(results: list[object]) -> None:
    messages = [
        str(item.get("error", ""))
        for item in results
        if isinstance(item, Mapping) and item.get("error")
    ]
    normalized = " ".join(messages).lower()
    transient_markers = {
        "rate_limit": ("429", "rate limit"),
        "connection": ("connection",),
        "eof": ("eof",),
        "ssl": ("ssl",),
        "timeout": ("timeout", "timed out"),
        "unavailable": ("temporarily unavailable",),
    }
    for diagnostic_kind, markers in transient_markers.items():
        if any(marker in normalized for marker in markers):
            raise MineruUnavailableError(
                diagnostic_stage="result",
                diagnostic_kind=diagnostic_kind,
            )
    raise MineruUnreadableError


def _classify_tool_error(error: Exception) -> MineruMcpError:
    status_code = getattr(error, "status_code", None)
    if status_code == 429 or (isinstance(status_code, int) and status_code >= 500):
        return MineruUnavailableError()
    if isinstance(error, (ConnectionError, OSError)):
        return MineruUnavailableError()
    return MineruUnreadableError()
