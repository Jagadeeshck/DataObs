from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import TypeVar

from .models import LifecycleEvent, Record

T = TypeVar("T", bound=Record)


class ConflictError(ValueError):
    pass


class InMemoryLifecycleRepository:
    """Thread-compatible interface; production adapter uses Elasticsearch OCC."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Record]] = defaultdict(dict)
        self._events: list[LifecycleEvent] = []
        self._idempotency: dict[str, Record] = {}

    def create(self, kind: str, record: T, idempotency_key: str) -> T:
        previous = self._idempotency.get(f"{kind}:{idempotency_key}")
        if previous:
            return deepcopy(previous)  # type: ignore[return-value]
        if record.id in self._records[kind]:
            raise ConflictError(f"{kind} already exists")
        self._records[kind][record.id] = deepcopy(record)
        self._idempotency[f"{kind}:{idempotency_key}"] = deepcopy(record)
        return deepcopy(record)

    def get(self, kind: str, record_id: str) -> Record:
        try:
            return deepcopy(self._records[kind][record_id])
        except KeyError as exc:
            raise KeyError(f"{kind} not found") from exc

    def list(self, kind: str) -> list[Record]:
        return [deepcopy(item) for _, item in sorted(self._records[kind].items())]

    def save(self, kind: str, record: T, expected_revision: int) -> T:
        current: Record = self.get(kind, record.id)
        if current.revision != expected_revision:
            raise ConflictError("revision conflict")
        self._records[kind][record.id] = deepcopy(record)
        return deepcopy(record)

    def append_event(self, event: LifecycleEvent) -> None:
        self._events.append(event)

    def events(self) -> tuple[LifecycleEvent, ...]:
        return tuple(self._events)
