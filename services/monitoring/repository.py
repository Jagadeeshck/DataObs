"""Durable repository contracts for the monitor runtime.

Production implementations must persist every transition and always scope reads by
tenant and environment.  The protocol deliberately makes that scope impossible to
omit from history and lease operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Protocol, Sequence

from packages.domain_model.monitor import MonitorDefinition, MonitorEvaluation, MonitorFinding, MonitorObservation


class VersionConflict(RuntimeError):
    """The supplied optimistic-concurrency token is stale."""


class MonitorRepository(Protocol):
    def get_monitor(self, tenant_id: str, environment: str, monitor_id: str) -> MonitorDefinition | None: ...
    def list_due_schedules(
        self, tenant_id: str, environment: str, before: datetime, limit: int
    ) -> Sequence[dict[str, Any]]: ...
    def acquire_lease(
        self, tenant_id: str, environment: str, lease_id: str, owner: str, now: datetime, expires_at: datetime
    ) -> bool: ...
    def renew_lease(
        self, tenant_id: str, environment: str, lease_id: str, owner: str, expires_at: datetime
    ) -> bool: ...
    def release_lease(self, tenant_id: str, environment: str, lease_id: str, owner: str) -> bool: ...
    def history(
        self, tenant_id: str, environment: str, monitor_id: str, before: datetime, limit: int
    ) -> Sequence[MonitorObservation]: ...
    def save_evaluation(self, evaluation: MonitorEvaluation, *, idempotency_key: str) -> bool: ...
    def save_finding(self, finding: MonitorFinding, *, idempotency_key: str) -> bool: ...
    def bulk_observations(self, observations: Iterable[MonitorObservation]) -> int: ...
    def checkpoint(
        self, tenant_id: str, environment: str, monitor_id: str, value: dict[str, Any], *, expected_revision: int | None
    ) -> int: ...
