from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Protocol


@dataclass(frozen=True)
class PaginationCursor:
    value: str


@dataclass(frozen=True)
class CollectionCheckpoint:
    tenant_id: str
    integration_id: str
    provider_type: str
    capability: str
    cursor: PaginationCursor | None = None
    watermark: datetime | None = None
    version: int = 0
    scope: Mapping[str, str] = field(default_factory=dict)


class CheckpointStore(Protocol):
    async def load(
        self, tenant_id: str, integration_id: str, capability: str, *, scope: Mapping[str, str] | None = None
    ) -> CollectionCheckpoint | None: ...

    async def save(self, checkpoint: CollectionCheckpoint, *, expected_version: int | None) -> None: ...


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str, tuple[tuple[str, str], ...]], CollectionCheckpoint] = {}

    async def load(
        self, tenant_id: str, integration_id: str, capability: str, *, scope=None
    ) -> CollectionCheckpoint | None:
        return self._items.get((tenant_id, integration_id, capability, tuple(sorted((scope or {}).items()))))

    async def save(self, checkpoint: CollectionCheckpoint, *, expected_version: int | None) -> None:
        from .errors import CheckpointConflictError

        key = (
            checkpoint.tenant_id,
            checkpoint.integration_id,
            checkpoint.capability,
            tuple(sorted(checkpoint.scope.items())),
        )
        current = self._items.get(key)
        if expected_version is None and current is not None:
            raise CheckpointConflictError("checkpoint already exists")
        if expected_version is not None and (current is None or current.version != expected_version):
            raise CheckpointConflictError("checkpoint version conflict")
        self._items[key] = checkpoint
