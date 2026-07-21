"""Bounded replay of event-first monitor definition operations."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable

from packages.domain_model.monitor import MonitorDefinition
from services.monitoring.definition_events import DefinitionOperation, canonical_checksum
from services.monitoring.repository import ConsistencyError, VersionConflict


def apply_operation(repo, operation: DefinitionOperation) -> DefinitionOperation:
    current = repo.get_monitor(operation.tenant_id, operation.environment, operation.monitor_id)
    if current and current.revision > operation.revision:
        return replace(operation, state="superseded")
    if current and current.revision == operation.revision:
        if canonical_checksum(current) != operation.checksum:
            raise ConsistencyError("divergent same-revision monitor definition")
        return replace(operation, state="applied")
    monitor = MonitorDefinition.model_validate(operation.definition)
    try:
        if current is None:
            repo.create_monitor(monitor)
        else:
            repo.update_monitor(monitor, expected_etag=current.etag)
    except VersionConflict:
        return replace(operation, state="superseded")
    return replace(operation, state="applied")


def reconcile(
    operations: Iterable[DefinitionOperation],
    repo,
    *,
    limit: int = 100,
    checkpoint: Callable[[str], None] | None = None,
) -> list[DefinitionOperation]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    outcomes: list[DefinitionOperation] = []
    for operation in operations:
        if len(outcomes) >= limit or operation.state != "pending":
            break
        outcome = apply_operation(repo, operation)
        outcomes.append(outcome)
        if checkpoint:
            checkpoint(outcome.operation_id)
    return outcomes
