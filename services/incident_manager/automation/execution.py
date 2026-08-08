from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .catalogue import canonical_hash
from .contracts import ActionExecutor, Execution, ExecutionState
from .repository import AutomationRepository, Conflict

MAX_BATCH = 25
MAX_LEASE_SECONDS = 60


class ExecutorRegistry:
    def __init__(self, executors: tuple[ActionExecutor, ...] = ()) -> None:
        self._executors = {executor.action_type: executor for executor in executors}

    def require(self, action_type: str) -> ActionExecutor:
        try:
            return self._executors[action_type]
        except KeyError as exc:
            raise LookupError("executor not configured") from exc


class ExecutionWorker:
    def __init__(self, repository: AutomationRepository, registry: ExecutorRegistry, worker_id: str) -> None:
        self.repository, self.registry, self.worker_id = repository, registry, worker_id

    def claim(self, execution: Execution, now: datetime | None = None) -> Execution:
        checked = now or datetime.now(timezone.utc)
        if execution.state != ExecutionState.QUEUED:
            raise Conflict("execution is not claimable")
        old_fence = execution.lease_token
        execution.state = ExecutionState.CLAIMED
        execution.lease_owner = self.worker_id
        execution.lease_token += 1
        execution.lease_expires_at = checked + timedelta(seconds=MAX_LEASE_SECONDS)
        execution.updated_at = checked
        return self.repository.update_execution(execution, old_fence)

    def run_once(self, limit: int = MAX_BATCH, now: datetime | None = None) -> int:
        checked = now or datetime.now(timezone.utc)
        processed = 0
        for queued in self.repository.queued(min(max(limit, 1), MAX_BATCH), checked):
            try:
                item = self.claim(queued, checked)
            except Conflict:
                continue
            try:
                executor = self.registry.require(item.action_type)
            except LookupError:
                item.state, item.error_code = ExecutionState.FAILED, "executor_not_configured"
                self.repository.update_execution(item, item.lease_token)
                processed += 1
                continue
            item.state, item.attempt, item.updated_at = ExecutionState.RUNNING, item.attempt + 1, checked
            self.repository.update_execution(item, item.lease_token)
            result = executor.execute(item)
            item.operation_reference = result.operation_reference[:200]
            item.updated_at = datetime.now(timezone.utc)
            if result.accepted:
                item.state = ExecutionState.VERIFICATION_PENDING
            elif result.retryable and item.attempt < item.max_attempts:
                item.state = ExecutionState.QUEUED
                item.lease_owner = None
                item.lease_expires_at = None
            else:
                item.state, item.error_code = ExecutionState.FAILED, "provider_operation_failed"
            self.repository.update_execution(item, item.lease_token)
            self.repository.append_event(
                "remediation_action",
                canonical_hash([item.execution_id, item.state.value, item.attempt]),
                {
                    "@timestamp": item.updated_at.isoformat(),
                    "tenant_id": item.tenant_id,
                    "environment": item.environment,
                    "incident_id": item.incident_id,
                    "workflow_execution_id": item.execution_id,
                    "event_type": f"execution_{item.state.value}",
                    "action_type": item.action_type,
                    "retry_count": item.attempt - 1,
                    "terminal_state": item.state in {ExecutionState.FAILED, ExecutionState.CANCELLED},
                    "request_id": item.request_id,
                    "correlation_id": item.action_fingerprint,
                    "metadata": {"catalogue_hash": item.catalogue_hash, "policy_hash": item.policy_hash},
                },
            )
            processed += 1
        return processed
