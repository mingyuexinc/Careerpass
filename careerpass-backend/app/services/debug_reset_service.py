"""Development-only current-account reset use case."""

from __future__ import annotations

import logging

from app.core.identity import CurrentIdentity
from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.debug_reset_repository import (
    DebugResetRepository,
    ResetAccountBusyError,
    ResetAccountConflictError,
)
from app.repositories.object_storage_repository import ObjectStorageRepository

logger = logging.getLogger("careerpass.debug_reset")


class DebugResetDisabledError(Exception):
    """Raised when the destructive development endpoint is disabled."""


class DebugResetService:
    """Reset only the resources owned by the authenticated current identity."""

    def __init__(
        self,
        *,
        repository: DebugResetRepository,
        object_repository: ObjectStorageRepository,
        storage: LocalObjectStorage,
        enabled: bool,
    ) -> None:
        self._repository = repository
        self._object_repository = object_repository
        self._storage = storage
        self._enabled = enabled

    async def reset_current_account(self, identity: CurrentIdentity) -> None:
        if not self._enabled:
            raise DebugResetDisabledError
        async with self._repository.transaction():
            resources = await self._repository.reset_current_account(identity)

        failed_deletions = 0
        for claim in resources.storage_claims:
            try:
                self._storage.delete(claim.storage_key)
            except OSError:
                failed_deletions += 1
                continue
            await self._object_repository.finalize_deletion(claim.object_id)
        if failed_deletions:
            logger.warning(
                "debug reset left physical object cleanup pending role=%s count=%d",
                identity.active_role,
                failed_deletions,
            )


__all__ = [
    "DebugResetDisabledError",
    "DebugResetService",
    "ResetAccountBusyError",
    "ResetAccountConflictError",
]
