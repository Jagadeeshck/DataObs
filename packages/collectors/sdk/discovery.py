from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .capabilities import Capability
from .checkpoints import CollectionCheckpoint, PaginationCursor


@dataclass(frozen=True)
class DiscoveryRequest:
    page_size: int = 100
    cursor: PaginationCursor | None = None
    filters: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")


@dataclass(frozen=True)
class CollectionRequest:
    capabilities: frozenset[Capability]
    checkpoint: CollectionCheckpoint | None = None
    page_size: int = 100

    def __post_init__(self) -> None:
        if not self.capabilities:
            raise ValueError("at least one capability is required")
        if not 1 <= self.page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
