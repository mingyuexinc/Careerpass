"""Storage adapters."""

from app.infrastructure.storage.controlled import ControlledJobDescriptionStorage
from app.infrastructure.storage.local import LocalObjectStorage

__all__ = ["ControlledJobDescriptionStorage", "LocalObjectStorage"]
