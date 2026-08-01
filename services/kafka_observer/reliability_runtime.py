"""Durable orchestration primitives for the Team 1 reliability worker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from packages.streaming.reliability import Definition, Evaluation, Observation, PreviousState, evaluate


class StaleWriter(RuntimeError):
    pass


class Store(Protocol):
    def acquire(self, scope: str, worker: str, expires_at: datetime) -> int | None: ...
    def due(self, tenant: str, environment: str, now: datetime, limit: int) -> list[Definition]: ...
    def previous(self, definition: Definition) -> PreviousState: ...
    def persist(self, evaluation: Evaluation, definition: Definition, fencing_token: int) -> bool: ...
    def checkpoint(self, definition: Definition, evaluation_id: str, fencing_token: int) -> None: ...


@dataclass
class RuntimeHealth:
    configured: bool = True
    worker_id: str = ""
    lease_status: str = "idle"
    definitions_due: int = 0
    definitions_evaluated: int = 0
    definitions_skipped: int = 0
    latest_successful_evaluation: datetime | None = None
    latest_failed_evaluation: datetime | None = None
    consecutive_failures: int = 0
    checkpoint_status: str = "idle"
    elasticsearch_status: str = "unknown"


class ReliabilityRuntime:
    MAX_DEFINITIONS = 200

    def __init__(self, store: Store, observe: Callable[[Definition, datetime, datetime], Observation], worker_id: str):
        self.store, self.observe, self.health = store, observe, RuntimeHealth(worker_id=worker_id)
        self.stopping = False

    def stop(self) -> None:
        self.stopping = True

    def run_once(self, tenant: str, environment: str, now: datetime | None = None) -> list[Evaluation]:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        scope = f"{tenant}:{environment}"
        token = self.store.acquire(scope, self.health.worker_id, now + timedelta(seconds=90))
        if token is None:
            self.health.lease_status = "contended"
            return []
        self.health.lease_status, self.health.elasticsearch_status = "held", "available"
        definitions = self.store.due(tenant, environment, now, self.MAX_DEFINITIONS)
        self.health.definitions_due = len(definitions)
        completed: list[Evaluation] = []
        for definition in definitions:
            if self.stopping:
                self.health.definitions_skipped += 1
                break
            try:
                start = now - timedelta(seconds=definition.evaluation_window_seconds)
                result = evaluate(
                    definition, self.observe(definition, start, now), self.store.previous(definition), now
                )
                # append-only persistence is deliberately ordered before checkpointing
                self.store.persist(result, definition, token)
                self.store.checkpoint(definition, result.evaluation_id, token)
                completed.append(result)
                self.health.definitions_evaluated += 1
                self.health.latest_successful_evaluation = now
                self.health.consecutive_failures = 0
                self.health.checkpoint_status = "advanced"
            except Exception:
                self.health.latest_failed_evaluation = now
                self.health.consecutive_failures += 1
                self.health.checkpoint_status = "not_advanced"
        return completed
