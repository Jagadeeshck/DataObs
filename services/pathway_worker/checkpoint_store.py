from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Checkpoint:
    tenant_id: str
    source: str
    last_timestamp: str
    last_id: str
    revision: int = 1


def search_after(checkpoint: Checkpoint) -> list[str]:
    return [checkpoint.last_timestamp, checkpoint.last_id]
