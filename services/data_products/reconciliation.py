from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from typing import Any, Literal, Protocol

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductRevisionEvent
from services.data_products.operation_state import (
    DataProductOperationCheckpoint,
    DataProductOperationClaim,
    DataProductOperationFinalResult,
    DataProductOperationPlan,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
    OperationClaimConflict,
    OperationConsistencyError,
)
from services.data_products.repository import DataProductRepository


@dataclass(frozen=True)
class OperationReconciliationContext:
    worker_id: str
    now: Any


@dataclass(frozen=True)
class OperationReconciliationOutcome:
    status: Literal["applied", "superseded", "failed", "retry"]
    checkpoint: str | None = None
    final_result: Mapping[str, Any] | None = None
    error_code: str | None = None
    retryable: bool = False


class OperationReconciliationHandler(Protocol):
    def reconcile(self, repository, state, claim, history, plan) -> OperationReconciliationOutcome: ...


class DurablePlanHandler:
    """Common recovery handler; operation services may supply projection-specific callbacks in the plan."""

    def reconcile(self, repository, state, claim, history, plan):
        if plan.operation_kind != state.operation_kind or plan.reference != state.plan_reference:
            raise OperationConsistencyError("operation_plan_mismatch")
        result = repository.load_operation_result(
            state.tenant_id, state.environment, state.product_id, state.operation_id
        )
        if result:
            if result.reference != state.result_reference and state.result_reference is not None:
                raise OperationConsistencyError("operation_result_mismatch")
            return OperationReconciliationOutcome("applied", "result_persisted", result.payload)
        payload = plan.payload.get("result")
        if not isinstance(payload, Mapping):
            return OperationReconciliationOutcome(
                "retry", state.last_checkpoint.name if state.last_checkpoint else None, retryable=True
            )
        return OperationReconciliationOutcome("applied", "projections_verified", payload)


class OperationReconciliationRegistry:
    REQUIRED_KINDS = (
        "manual_membership",
        "proposal_accept",
        "proposal_reject",
        "proposal_expire",
        "proposal_supersede",
        "membership_exclude",
        "dependency_replace",
        "product_lifecycle",
    )

    def __init__(self, handlers: Mapping[str, OperationReconciliationHandler] | None = None) -> None:
        default = DurablePlanHandler()
        self._handlers: dict[str, OperationReconciliationHandler] = {kind: default for kind in self.REQUIRED_KINDS}
        if handlers:
            self._handlers.update(handlers)

    def get(self, operation_kind: str) -> OperationReconciliationHandler:
        try:
            return self._handlers[operation_kind]
        except KeyError as exc:
            raise OperationConsistencyError("unknown_operation_kind") from exc


def _checksum(payload: Mapping[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class DataProductOperationService:
    """Independently runnable, CAS-fenced operation reconciliation service."""

    def __init__(
        self, repository: DataProductRepository, *, worker_id: str, claim_ttl_seconds: int = 30, registry=None
    ) -> None:
        self.repository = repository
        self.worker_id = worker_id
        self.claim_ttl_seconds = claim_ttl_seconds
        self.registry = registry or OperationReconciliationRegistry()

    def get_operation_status(self, tenant_id: str, environment: str, operation_id: str):
        return self.repository.get_operation_state(tenant_id, environment, operation_id)

    def reconcile_operation(self, tenant_id: str, environment: str, operation_id: str) -> str:
        state = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if state is None:
            return "missing"
        if state.status in {"applied", "superseded", "failed"}:
            return state.status
        now = utc_now()
        try:
            claim = self.repository.claim_operation(
                tenant_id,
                environment,
                operation_id,
                worker_id=self.worker_id,
                now=now,
                expires_at=now + timedelta(seconds=self.claim_ttl_seconds),
                expected_seq_no=state.seq_no,
                expected_primary_term=state.primary_term,
            )
        except OperationClaimConflict:
            return "retry"
        claimed = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if claimed is None:
            return "missing"
        plan = self.repository.load_operation_plan(tenant_id, environment, claimed.product_id, operation_id)
        if plan is None:
            self.repository.fail_operation(claim, error_code="operation_plan_missing")
            return "failed"
        history = self.repository.get_operation_history(tenant_id, environment, operation_id)
        try:
            outcome = self.registry.get(claimed.operation_kind).reconcile(
                self.repository, claimed, claim, history, plan
            )
            if outcome.status == "retry":
                return "retry"
            checkpoint_name = outcome.checkpoint or "projections_verified"
            checkpoint = DataProductOperationCheckpoint(checkpoint_name, plan.checksum, utc_now())
            self.repository.checkpoint_operation(claim, checkpoint)
            if outcome.status == "applied":
                payload = outcome.final_result or {}
                checksum = _checksum(payload)
                result = DataProductOperationResultEnvelope(
                    f"result:{operation_id}:{checksum}",
                    tenant_id,
                    environment,
                    claimed.product_id,
                    operation_id,
                    checksum,
                    payload,
                    utc_now(),
                )
                self.repository.save_operation_result(result)
                self.repository.complete_operation(
                    claim,
                    DataProductOperationFinalResult(
                        int(payload.get("revision", 0)),
                        str(payload.get("etag", "recovered")),
                        result.reference,
                        result.created_at,
                    ),
                )
                if claimed.idempotency_record_id:
                    self.repository.repair_idempotency_completion(
                        claimed.idempotency_record_id,
                        DataProductOperationFinalResult(
                            int(payload.get("revision", 0)),
                            str(payload.get("etag", "recovered")),
                            result.reference,
                            result.created_at,
                        ),
                    )
                return "applied"
            if outcome.status == "superseded":
                self.repository.supersede_operation(claim, error_code=outcome.error_code or "newer_operation")
                return "superseded"
            self.repository.fail_operation(claim, error_code=outcome.error_code or "reconciliation_failed")
            return "failed"
        except OperationClaimConflict:
            return "retry"
        except OperationConsistencyError as exc:
            try:
                self.repository.fail_operation(claim, error_code=exc.code)
            except OperationClaimConflict:
                return "retry"
            return "failed"

    def reconcile_batch(self, tenant_id: str, environment: str, *, limit: int = 100) -> dict[str, int]:
        if not 1 <= limit <= 1000:
            raise ValueError("reconciliation limit outside bounds")
        outcomes = {"applied": 0, "superseded": 0, "failed": 0, "retry": 0, "missing": 0}
        for state in self.repository.list_reconcilable_operations(tenant_id, environment, limit=limit):
            outcome = self.reconcile_operation(tenant_id, environment, state.operation_id)
            outcomes[outcome] += 1
        return outcomes


class DataProductReconciler:
    """Bounded reconciliation facade. Claiming and fencing remain repository-owned."""

    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def reconcile_operation(self, tenant_id: str, environment: str, operation_id: str) -> str:
        event = self.repository.get_operation(tenant_id, environment, operation_id)
        if event is None:
            return "missing"
        current = self.repository.get_product(tenant_id, environment, event.product_id)
        if current and current.revision == event.revision and current.etag == event.etag:
            if event.outcome == "pending":
                self.repository.finish_operation(
                    event.model_copy(update={"outcome": "applied", "applied_at": current.updated_at})
                )
            return "applied"
        if current and current.revision > event.revision:
            self.repository.finish_operation(event.model_copy(update={"outcome": "superseded"}))
            return "superseded"
        return "retry"

    def reconcile_proposal_decision(self, tenant_id: str, environment: str, product_id: str, proposal_id: str) -> str:
        """Inspect immutable evidence and projection without inventing a cross-index transaction."""
        proposal = self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
        if proposal is None:
            return "missing"
        decisions = self.repository.list_membership_decisions(tenant_id, environment, product_id, limit=200).items
        terminal = [event for event in decisions if event.proposal_id == proposal_id and event.outcome == "applied"]
        if terminal and proposal.state != "proposed":
            return "applied"
        if proposal.state != "proposed":
            return "terminal_evidence_missing"
        return "retry"

    def reconcile_membership_exclusion(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> str:
        membership = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
        if membership is None:
            return "missing"
        decisions = self.repository.list_membership_decisions(tenant_id, environment, product_id, limit=200).items
        terminal = [
            event
            for event in decisions
            if event.membership_id == membership_id and event.decision == "exclude" and event.outcome == "applied"
        ]
        if membership.state == "excluded" and terminal:
            return "applied"
        if membership.state == "excluded":
            return "terminal_evidence_missing"
        return "retry"

    def run(self, tenant_id: str, environment: str, *, limit: int = 100) -> dict[str, int]:
        events = self.repository.list_pending_operations(tenant_id, environment, limit=limit)
        outcomes = {"applied": 0, "superseded": 0, "retry": 0, "missing": 0}
        for event in events:
            outcome = self.reconcile_operation(tenant_id, environment, event.operation_id)
            outcomes[outcome] += 1
        return outcomes


OperationReconciler = DataProductReconciler


def reconcile_pending(
    events: Iterable[DataProductRevisionEvent], apply: Callable[[DataProductRevisionEvent], None], *, limit: int = 100
) -> int:
    """Apply a deterministic bounded batch; callers persist applied/superseded outcomes."""
    if not 1 <= limit <= 1000:
        raise ValueError("reconciliation limit outside bounds")
    pending = sorted(
        (event for event in events if event.outcome == "pending"), key=lambda e: (e.revision, e.operation_id)
    )
    for event in pending[:limit]:
        apply(event)
    return min(len(pending), limit)
