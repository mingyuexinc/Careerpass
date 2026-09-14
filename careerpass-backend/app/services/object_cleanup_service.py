"""Application service for idempotent, reference-safe object cleanup."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.object_storage_repository import ObjectStorageRepository

logger = logging.getLogger("careerpass.object_cleanup")


class ObjectCleanupService:
    """Delete only expired, unreferenced objects while preserving retryable failures."""

    def __init__(self, *, repository: ObjectStorageRepository, storage: LocalObjectStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def run_once(self, *, batch_size: int = 100) -> int:
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be between 1 and 500")
        claims = await self._repository.claim_expired_unreferenced(
            older_than=datetime.now(UTC) - timedelta(hours=1),
            limit=batch_size,
        )
        deleted = 0
        finalize_failures = 0
        for claim in claims:
            try:
                self._storage.delete(claim.storage_key)
            except OSError:
                await self._repository.restore_after_delete_failure(claim)
                continue
            try:
                if await self._repository.finalize_deletion(claim.object_id):
                    deleted += 1
            except Exception:
                # The claimed row stays deleting and is re-claimed next cycle.
                finalize_failures += 1
        if finalize_failures:
            logger.warning(
                "object cleanup finalize failed and stays retryable count=%d",
                finalize_failures,
            )
        return deleted
