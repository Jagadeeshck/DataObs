"""Scanner worker execution primitives.

The in-memory lease manager in this module is intended for development and unit
 tests only. Production scheduling will use a durable, distributed lease backend.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.agent_sdk.models import (
    BaseRequest,
    ConnectorIdentity,
    ErrorCategory,
    ResultMetadata,
    ScanError,
    ScanExecution,
    ScannerHeartbeat,
    ScanTask,
    TaskLease,
)
from packages.agent_sdk.security import redact


class InMemoryLeaseManager:
    """Development/test-only lease manager; not safe for distributed workers."""

    def acquire(self, task: ScanTask, owner: str) -> TaskLease:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=task.timeout_seconds)
        return TaskLease(task.task_id, owner, expires_at)

    def renew(self, lease: TaskLease) -> TaskLease:
        lease.version += 1
        return lease


class ScannerWorker:
    """Execute scanner tasks through registered connectors."""

    def __init__(
        self, registry: Any, lease_manager: InMemoryLeaseManager | None = None, worker_id: str | None = None
    ) -> None:
        self.registry = registry
        self.lease_manager = lease_manager or InMemoryLeaseManager()
        self.worker_id = worker_id or "scanner-" + uuid.uuid4().hex[:8]
        self.heartbeats: list[ScannerHeartbeat] = []

    def heartbeat(self, task: ScanTask, connector: Any) -> ScannerHeartbeat:
        heartbeat = ScannerHeartbeat(
            self.worker_id,
            task.tenant_id,
            task.environment,
            True,
            connector.capabilities(),
        )
        self.heartbeats.append(heartbeat)
        return heartbeat

    def _metadata(self, task: ScanTask) -> ResultMetadata:
        return ResultMetadata(
            task.tenant_id,
            task.environment,
            task.integration_id,
            ConnectorIdentity(task.connector_name, "0.1.0", task.source_system),
            "exec-" + task.task_id,
            task.task_id,
            datetime.now(timezone.utc),
            None,
            task.source_system,
            task.asset_filter.get("asset", "*"),
            correlation_trace_id=task.options.get("trace_id"),
        )

    def run(self, task: ScanTask) -> ScanExecution:
        task.validate()
        connector = self.registry.create(task.connector_name)
        lease = self.lease_manager.acquire(task, self.worker_id)
        self.heartbeat(task, connector)
        metadata = self._metadata(task)
        request = BaseRequest(metadata, task.options)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(getattr(connector, task.operation), request)
                try:
                    result = future.result(timeout=task.timeout_seconds)
                    return ScanExecution(metadata, lease, result, attempts=task.attempt)
                except TimeoutError:
                    future.cancel()
                    return ScanExecution(
                        metadata,
                        lease,
                        None,
                        ScanError(ErrorCategory.timeout, "task timed out", True),
                        task.attempt,
                    )
                except Exception as exc:  # noqa: BLE001 - connector errors are captured and redacted.
                    return ScanExecution(
                        metadata,
                        lease,
                        None,
                        ScanError(ErrorCategory.connector, str(redact(str(exc))), task.attempt < 3),
                        task.attempt,
                    )
        finally:
            close = getattr(connector, "close", None)
            if callable(close):
                close()


def deterministic_retry_delay(attempt: int, base_seconds: int = 5) -> int:
    """Return bounded exponential backoff in seconds."""

    return min(base_seconds * (2 ** max(0, attempt - 1)), 300)
