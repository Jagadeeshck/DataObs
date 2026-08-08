from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Protocol

from .contracts import Approval, Execution, Preview


class Conflict(RuntimeError):
    pass


class AutomationRepository(Protocol):
    def save_preview(self, preview: Preview) -> Preview: ...
    def get_preview(self, tenant_id: str, environment: str, preview_id: str) -> Preview | None: ...
    def create_approval(self, approval: Approval) -> Approval: ...
    def get_approval(self, tenant_id: str, environment: str, approval_id: str) -> Approval | None: ...
    def update_approval(self, approval: Approval, expected_revision: int) -> Approval: ...
    def create_execution(self, execution: Execution, idempotency_fingerprint: str) -> Execution: ...
    def get_execution(self, tenant_id: str, environment: str, execution_id: str) -> Execution | None: ...
    def update_execution(self, execution: Execution, expected_lease_token: int | None = None) -> Execution: ...
    def queued(self, limit: int, now: datetime) -> list[Execution]: ...
    def incomplete_executions(self, limit: int, now: datetime) -> list[Execution]: ...
    def executions_with_pending_evidence(self, limit: int) -> list[Execution]: ...
    def approvals_requiring_reconciliation(self, limit: int, now: datetime) -> list[Approval]: ...
    def append_event(self, stream: str, event_id: str, document: dict[str, object]) -> None: ...


class InMemoryAutomationRepository:
    """Thread-safe test adapter; production composition uses ElasticsearchAutomationRepository."""

    def __init__(self) -> None:
        self.previews: dict[str, Preview] = {}
        self.approvals: dict[str, Approval] = {}
        self.executions: dict[str, Execution] = {}
        self.idempotency: dict[str, str] = {}
        self.events: dict[str, dict[str, object]] = {}
        self.lock = Lock()

    def save_preview(self, preview: Preview) -> Preview:
        with self.lock:
            instances = [
                item
                for item in self.previews.values()
                if item.action_fingerprint == preview.action_fingerprint
                and (item.tenant_id, item.environment) == (preview.tenant_id, preview.environment)
            ]
            live = [item for item in instances if item.expires_at > preview.previewed_at]
            if live:
                return max(live, key=lambda item: item.preview_generation).model_copy(deep=True)
            generation = max((item.preview_generation for item in instances), default=0) + 1
            from .catalogue import canonical_hash

            candidate = preview.model_copy(
                update={
                    "preview_generation": generation,
                    "preview_id": f"prv_{canonical_hash([preview.action_fingerprint, generation])}",
                }
            )
            self.previews.setdefault(candidate.preview_id, candidate)
            return self.previews[candidate.preview_id].model_copy(deep=True)

    def get_preview(self, tenant_id: str, environment: str, preview_id: str) -> Preview | None:
        item = self.previews.get(preview_id)
        return deepcopy(item) if item and (item.tenant_id, item.environment) == (tenant_id, environment) else None

    def create_approval(self, approval: Approval) -> Approval:
        with self.lock:
            current = self.approvals.setdefault(approval.approval_id, approval.model_copy(deep=True))
            if current.action_fingerprint != approval.action_fingerprint:
                raise Conflict("approval idempotency conflict")
            return current.model_copy(deep=True)

    def get_approval(self, tenant_id: str, environment: str, approval_id: str) -> Approval | None:
        item = self.approvals.get(approval_id)
        return (
            item.model_copy(deep=True)
            if item and (item.tenant_id, item.environment) == (tenant_id, environment)
            else None
        )

    def update_approval(self, approval: Approval, expected_revision: int) -> Approval:
        with self.lock:
            current = self.approvals.get(approval.approval_id)
            if not current or current.revision != expected_revision:
                raise Conflict("approval revision conflict")
            approval.revision = expected_revision + 1
            self.approvals[approval.approval_id] = approval.model_copy(deep=True)
            return approval.model_copy(deep=True)

    def create_execution(self, execution: Execution, idempotency_fingerprint: str) -> Execution:
        with self.lock:
            existing_hash = self.idempotency.get(execution.execution_id)
            if existing_hash and existing_hash != idempotency_fingerprint:
                raise Conflict("idempotency key was already used for another action")
            self.idempotency[execution.execution_id] = idempotency_fingerprint
            self.executions.setdefault(execution.execution_id, execution.model_copy(deep=True))
            return self.executions[execution.execution_id].model_copy(deep=True)

    def get_execution(self, tenant_id: str, environment: str, execution_id: str) -> Execution | None:
        item = self.executions.get(execution_id)
        return (
            item.model_copy(deep=True)
            if item and (item.tenant_id, item.environment) == (tenant_id, environment)
            else None
        )

    def update_execution(self, execution: Execution, expected_lease_token: int | None = None) -> Execution:
        with self.lock:
            current = self.executions.get(execution.execution_id)
            if not current or (expected_lease_token is not None and current.lease_token != expected_lease_token):
                raise Conflict("execution fence conflict")
            self.executions[execution.execution_id] = execution.model_copy(deep=True)
            return execution.model_copy(deep=True)

    def queued(self, limit: int, now: datetime) -> list[Execution]:
        items = [item for item in self.executions.values() if item.state == "queued"]
        return [
            item.model_copy(deep=True) for item in sorted(items, key=lambda x: (x.created_at, x.execution_id))[:limit]
        ]

    def incomplete_executions(self, limit: int, now: datetime) -> list[Execution]:
        recoverable = {"claimed", "running", "reconciliation_required"}
        items = [
            item
            for item in self.executions.values()
            if item.state in recoverable and item.lease_expires_at is not None and item.lease_expires_at <= now
        ]
        return [item.model_copy(deep=True) for item in sorted(items, key=lambda value: value.updated_at)[:limit]]

    def executions_with_pending_evidence(self, limit: int) -> list[Execution]:
        items = [item for item in self.executions.values() if item.transition_event_pending]
        return [
            item.model_copy(deep=True)
            for item in sorted(items, key=lambda value: (value.updated_at, value.execution_id))[
                : min(max(limit, 1), 25)
            ]
        ]

    def approvals_requiring_reconciliation(self, limit: int, now: datetime) -> list[Approval]:
        items = [
            item
            for item in self.approvals.values()
            if item.decision_event_pending
            or item.state == "reserved"
            or (item.state == "approved" and item.expires_at <= now)
        ]
        return [item.model_copy(deep=True) for item in sorted(items, key=lambda value: value.requested_at)[:limit]]

    def append_event(self, stream: str, event_id: str, document: dict[str, object]) -> None:
        with self.lock:
            self.events.setdefault(f"{stream}:{event_id}", deepcopy(document))
