"""Opaque-key local storage; it deliberately never exposes filesystem paths."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredUpload:
    storage_key: str
    content_sha256: str
    size_bytes: int


class LocalObjectStorage:
    """Write and read opaque storage keys under one configured, non-static root."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def put(self, content: bytes) -> StoredUpload:
        if not content:
            raise ValueError("empty content")
        self._root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(content).hexdigest()
        storage_key = uuid4().hex
        target = self._path_for(storage_key)
        descriptor, temporary_name = tempfile.mkstemp(prefix="upload-", dir=self._root)
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, target)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
        return StoredUpload(storage_key=storage_key, content_sha256=digest, size_bytes=len(content))

    def read(self, storage_key: str) -> bytes:
        return self._path_for(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        self._path_for(storage_key).unlink(missing_ok=True)

    def _path_for(self, storage_key: str) -> Path:
        if len(storage_key) != 32 or any(
            character not in "0123456789abcdef" for character in storage_key
        ):
            raise ValueError("invalid storage key")
        return self._root / storage_key
