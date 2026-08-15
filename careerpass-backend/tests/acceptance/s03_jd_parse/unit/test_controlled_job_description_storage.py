"""Unit coverage for the S-03 controlled local path boundary."""

from pathlib import Path

import pytest

from app.infrastructure.storage.controlled import ControlledJobDescriptionStorage


def test_controlled_storage_reads_only_utf8_markdown_under_root(tmp_path: Path) -> None:
    root = tmp_path / "jd"
    root.mkdir()
    path = root / "role.md"
    path.write_text("# Role", encoding="utf-8")
    storage = ControlledJobDescriptionStorage(str(root))

    assert storage.read(str(path)) == b"# Role"
    with pytest.raises(ValueError):
        storage.read(str(tmp_path / "outside.md"))


def test_controlled_storage_rejects_non_markdown_and_invalid_utf8(tmp_path: Path) -> None:
    root = tmp_path / "jd"
    root.mkdir()
    text_file = root / "role.txt"
    text_file.write_text("role", encoding="utf-8")
    binary_file = root / "binary.md"
    binary_file.write_bytes(b"\xff")
    storage = ControlledJobDescriptionStorage(str(root))

    with pytest.raises(ValueError):
        storage.read(str(text_file))
    with pytest.raises(ValueError):
        storage.read(str(binary_file))
