from __future__ import annotations

from typing import Any


class DurableCheckpointStore:
    def __init__(self, repository: Any):
        self.repository = repository

    def load(self, provider: str) -> dict[str, Any] | None:
        return self.repository.load_checkpoint(provider)

    def save(self, provider: str, checkpoint: dict[str, Any]) -> None:
        self.repository.save_checkpoint(provider, checkpoint)
