"""Controlled local-file access used only by the internal S-03 verification API."""

from __future__ import annotations

from pathlib import Path


class ControlledJobDescriptionStorage:
    """Read UTF-8 Markdown only from one configured root without exposing paths."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def read(self, local_path: str) -> bytes:
        candidate = Path(local_path).expanduser().resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("path outside controlled root") from exc
        if candidate.suffix.lower() != ".md" or not candidate.is_file():
            raise ValueError("controlled Markdown file unavailable")
        try:
            content = candidate.read_bytes()
            content.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError("controlled Markdown file unavailable") from exc
        if not content:
            raise ValueError("controlled Markdown file unavailable")
        return content
