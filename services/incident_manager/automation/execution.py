from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event, Thread

from .catalogue import canonical_hash
from .contracts import ActionExecutor, Execution, ExecutionState
from .repository import AutomationRepository, Conflict

MAX_BATCH = 25
MAX_LEASE_SECONDS = 60
DEFAULT_HEARTBEAT_SECONDS = 15


class RetryableBeforeSubmission(RuntimeError):
    """The provider was definitely not called."""


class ProviderOutcomeUnknown(RuntimeError):
    """The provider may have accepted the operation; lookup is required."""


class NonRetryableExecutorFailure(RuntimeError):
    """A safe, known terminal executor failure."""


class ExecutorRegistry:
    def __init__(self, executors: tuple[ActionExecutor, ...] = ()) -> None:
        self._executors = {executor.action_type: executor for executor in executors}

    def require(self, action_type: str) -> ActionExecutor:
        try:
            return self._executors[action_type]
        except KeyError as exc:
            raise LookupError("executor not configured") from exc


class ExecutionWorker:
    def __init__(
        self,
        repository: AutomationRepository,
        registry: ExecutorRegistry,
        worker_id: str,
        *,
        lease_seconds: int = MAX_LEASE_SECONDS,
        heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS,
    ) -> None:
        if lease_seconds < 3 or heartbeat_seconds <= 0 or heartbeat_seconds > lease_seconds / 3:
            raise ValueError("heartbeat_seconds must be positive and no greater than lease_seconds / 3")
        self.repository, self.registry, self.worker_id = repository, registry, worker_id
        self.lease_seconds, self.heartbeat_seconds = lease_seconds, heartbeat_seconds

    def claim(self, execution: Execution, now: datetime | None = None) -> Execution:
        checked = now or datetime.now(timezone.utc)
        if execution.state != ExecutionState.QUEUED:
            raise Conflict("execution is not claimable")
        old_fence = execution.lease_token
        execution.state = ExecutionState.CLAIMED
        execution.lease_owner = self.worker_id
        execution.lease_token += 1
        execution.lease_expires_at = checked + timedelta(seconds=self.lease_seconds)
        execution.claimed_at = checked
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
            item.execution_started_at = checked
            self.repository.update_execution(item, item.lease_token)
            heartbeat_stop, heartbeat_lost = Event(), Event()
            heartbeat = Thread(target=self._heartbeat, args=(item, heartbeat_stop, heartbeat_lost), daemon=True)
            heartbeat.start()
            try:
                result = executor.execute(item)
            except RetryableBeforeSubmission:
                heartbeat_stop.set()
                heartbeat.join()
                if heartbeat_lost.is_set():
                    processed += 1
                    continue
                self._record_failure(item, "executor_retryable_before_submission", retry_safe=True)
                processed += 1
                continue
            except ProviderOutcomeUnknown:
                heartbeat_stop.set()
                heartbeat.join()
                if heartbeat_lost.is_set():
                    processed += 1
                    continue
                self._record_failure(item, "provider_outcome_unknown", uncertain=True)
                processed += 1
                continue
            except NonRetryableExecutorFailure:
                heartbeat_stop.set()
                heartbeat.join()
                if heartbeat_lost.is_set():
                    processed += 1
                    continue
                self._record_failure(item, "executor_non_retryable", retry_safe=False)
                processed += 1
                continue
            except Exception:
                heartbeat_stop.set()
                heartbeat.join()
                if heartbeat_lost.is_set():
                    processed += 1
                    continue
                # Never persist or log exception text: adapters may include credentials.
                self._record_failure(item, "unexpected_executor_failure", uncertain=True)
                processed += 1
                continue
            heartbeat_stop.set()
            heartbeat.join()
            if heartbeat_lost.is_set():
                # A provider may have completed, but this fence no longer owns durable evidence.
                processed += 1
                continue
            item.operation_reference = result.operation_reference[:200]
            item.updated_at = datetime.now(timezone.utc)
            if result.accepted:
                item.state = ExecutionState.VERIFICATION_PENDING
                item.provider_accepted_at = item.updated_at
                item.verification_started_at = item.updated_at
            elif result.retryable and item.attempt < item.max_attempts:
                item.state = ExecutionState.QUEUED
                item.lease_owner = None
                item.lease_expires_at = None
            else:
                item.state, item.error_code = ExecutionState.FAILED, "provider_operation_failed"
            event_id = canonical_hash([item.execution_id, item.state.value, item.attempt])
            item.transition_event_id = event_id
            item.transition_event_pending = True
            self.repository.update_execution(item, item.lease_token)
            try:
                self.repository.append_event(
                    "remediation_action",
                    event_id,
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
            except Exception:
                # Projection carries deterministic repair evidence; continue the batch.
                pass
            else:
                item.transition_event_pending = False
                self.repository.update_execution(item, item.lease_token)
            processed += 1
        return processed

    def _heartbeat(self, item: Execution, stopping: Event, lost: Event) -> None:
        while not stopping.wait(self.heartbeat_seconds):
            try:
                renewed = self.repository.renew_execution_lease(
                    item.tenant_id,
                    item.environment,
                    item.execution_id,
                    self.worker_id,
                    item.lease_token,
                    datetime.now(timezone.utc) + timedelta(seconds=self.lease_seconds),
                )
            except Exception:
                lost.set()
                return
            item.lease_expires_at = renewed.lease_expires_at

    def _record_failure(
        self, item: Execution, error_code: str, *, retry_safe: bool = False, uncertain: bool = False
    ) -> None:
        old_state = item.state
        item.error_code = error_code
        item.updated_at = datetime.now(timezone.utc)
        if retry_safe and item.attempt < item.max_attempts:
            item.state = ExecutionState.QUEUED
            item.lease_owner = None
            item.lease_expires_at = None
        elif uncertain:
            item.state = ExecutionState.RECONCILIATION_REQUIRED
        else:
            item.state = ExecutionState.FAILED
        event_id = canonical_hash([item.execution_id, item.state.value, item.attempt])
        item.transition_event_id = event_id
        item.transition_event_pending = True
        self.repository.update_execution(item, item.lease_token)
        try:
            self.repository.append_event(
                "remediation_action",
                event_id,
                {
                    "@timestamp": item.updated_at.isoformat(),
                    "tenant_id": item.tenant_id,
                    "environment": item.environment,
                    "incident_id": item.incident_id,
                    "workflow_execution_id": item.execution_id,
                    "event_type": f"execution_{item.state.value}",
                    "action_type": item.action_type,
                    "retry_count": max(item.attempt - 1, 0),
                    "terminal_state": item.state
                    in {ExecutionState.FAILED, ExecutionState.CANCELLED, ExecutionState.TIMED_OUT},
                    "request_id": item.request_id,
                    "correlation_id": item.action_fingerprint,
                    "metadata": {
                        "old_state": old_state.value,
                        "new_state": item.state.value,
                        "attempt": item.attempt,
                        "error_code": error_code,
                        "retryable": retry_safe,
                        "outcome_known": not uncertain,
                        "catalogue_hash": item.catalogue_hash,
                        "policy_hash": item.policy_hash,
                    },
                },
            )
        except Exception:
            return
        item.transition_event_pending = False
        try:
            self.repository.update_execution(item, item.lease_token)
        except Conflict:
            pass

    def recover_expired(self, limit: int = MAX_BATCH, now: datetime | None = None) -> int:
        checked = now or datetime.now(timezone.utc)
        recovered = 0
        for stale in self.repository.incomplete_executions(limit, checked):
            old_fence = stale.lease_token
            stale.lease_token += 1
            stale.lease_owner = self.worker_id
            stale.lease_expires_at = checked + timedelta(seconds=self.lease_seconds)
            stale.updated_at = checked
            try:
                stale = self.repository.update_execution(stale, old_fence)
            except Conflict:
                continue
            if stale.state == ExecutionState.CLAIMED:
                stale.state = ExecutionState.QUEUED
                stale.lease_owner = None
                stale.lease_expires_at = None
            else:
                stale.state = ExecutionState.RECONCILIATION_REQUIRED
                try:
                    result = self.registry.require(stale.action_type).lookup(stale)
                except Exception:
                    stale.error_code = "provider_lookup_unavailable"
                else:
                    stale.operation_reference = result.operation_reference[:200]
                    if result.accepted:
                        stale.state = ExecutionState.VERIFICATION_PENDING
                        stale.provider_accepted_at = checked
                        stale.verification_started_at = checked
                    elif result.terminal:
                        stale.state = ExecutionState.FAILED
                        stale.error_code = "provider_operation_failed"
            self.repository.update_execution(stale, stale.lease_token)
            recovered += 1
        return recovered
