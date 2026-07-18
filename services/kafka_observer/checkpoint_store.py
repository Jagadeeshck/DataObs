from __future__ import annotations

from typing import Any, Protocol


class CheckpointStore(Protocol):
    def load(self, provider: str) -> dict[str, Any] | None: ...
    def save(self, provider: str, checkpoint: dict[str, Any]) -> None: ...


class MemoryCheckpointStore:
    def __init__(self):
        self.values: dict[str, dict[str, Any]] = {}

    def load(self, provider: str):
        return self.values.get(provider)

    def save(self, provider: str, checkpoint: dict[str, Any]):
        self.values[provider] = dict(checkpoint)
