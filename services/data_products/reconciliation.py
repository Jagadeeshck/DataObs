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
    DataProductOperationHistoryEvent,
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


class ProjectionAwareHandler:
    """Fail-closed base class: durable intent is never treated as projection evidence."""

    operation_kind: str

    def _verify(self, state, plan) -> Mapping[str, Any]:
        if plan.operation_kind != self.operation_kind or state.operation_kind != self.operation_kind:
            raise OperationConsistencyError("handler_operation_kind_mismatch")
        if plan.reference != state.plan_reference or _checksum(plan.payload) != plan.checksum:
            raise OperationConsistencyError("operation_plan_mismatch")
        fingerprint = plan.payload.get("request_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise OperationConsistencyError("operation_fingerprint_missing")
        return plan.payload

    def _existing_result(self, repository, state):
        result = repository.load_operation_result(
            state.tenant_id, state.environment, state.product_id, state.operation_id
        )
        if result is not None and _checksum(result.payload) != result.checksum:
            raise OperationConsistencyError("operation_result_mismatch")
        return result


class ManualMembershipReconciliationHandler(ProjectionAwareHandler):
    operation_kind = "manual_membership"

    def reconcile(self, repository, state, claim, history, plan):
        payload = self._verify(state, plan)
        membership = repository.get_membership(
            state.tenant_id, state.environment, state.product_id, str(payload.get("membership_id", ""))
        )
        if membership is None:
            return OperationReconciliationOutcome("retry", "pending_history", retryable=True)
        if membership.entity_id != payload.get("entity_id") or membership.entity_type != payload.get("entity_type"):
            raise OperationConsistencyError("membership_projection_diverged")
        result = self._existing_result(repository, state)
        final = result.payload if result else {"revision": membership.revision, "etag": membership.etag}
        return OperationReconciliationOutcome("applied", "membership_verified", final)


class ProposalDecisionReconciliationHandler(ProjectionAwareHandler):
    action: str

    def reconcile(self, repository, state, claim, history, plan):
        payload = self._verify(state, plan)
        proposal = repository.get_membership_proposal(
            state.tenant_id, state.environment, state.product_id, str(payload.get("proposal_id", ""))
        )
        if proposal is None:
            raise OperationConsistencyError("proposal_missing")
        expected_state = {"accept": "accepted", "reject": "rejected", "expire": "expired", "supersede": "superseded"}[
            self.action
        ]
        if proposal.state == "proposed":
            return OperationReconciliationOutcome("retry", "pending_history", retryable=True)
        if proposal.state != expected_state:
            raise OperationConsistencyError("newer_proposal_decision")
        membership = None
        if self.action == "accept":
            membership = repository.get_membership(
                state.tenant_id, state.environment, state.product_id, str(payload.get("membership_id", ""))
            )
            if membership is None or membership.state != "active":
                return OperationReconciliationOutcome("retry", "proposal_transition_verified", retryable=True)
        result = self._existing_result(repository, state)
        final = (
            result.payload
            if result
            else {
                "revision": membership.revision if membership else proposal.revision,
                "etag": membership.etag if membership else proposal.etag,
            }
        )
        return OperationReconciliationOutcome("applied", "proposal_projection_verified", final)


class ProposalAcceptReconciliationHandler(ProposalDecisionReconciliationHandler):
    operation_kind, action = "proposal_accept", "accept"


class ProposalRejectReconciliationHandler(ProposalDecisionReconciliationHandler):
    operation_kind, action = "proposal_reject", "reject"


class ProposalExpireReconciliationHandler(ProposalDecisionReconciliationHandler):
    operation_kind, action = "proposal_expire", "expire"


class ProposalSupersedeReconciliationHandler(ProposalDecisionReconciliationHandler):
    operation_kind, action = "proposal_supersede", "supersede"


class MembershipExclusionReconciliationHandler(ProjectionAwareHandler):
    operation_kind = "membership_exclude"

    def reconcile(self, repository, state, claim, history, plan):
        payload = self._verify(state, plan)
        membership = repository.get_membership(
            state.tenant_id, state.environment, state.product_id, str(payload.get("membership_id", ""))
        )
        if membership is None:
            raise OperationConsistencyError("membership_missing")
        if membership.state != "excluded":
            return OperationReconciliationOutcome("retry", "pending_history", retryable=True)
        result = self._existing_result(repository, state)
        return OperationReconciliationOutcome(
            "applied",
            "exclusion_verified",
            result.payload if result else {"revision": membership.revision, "etag": membership.etag},
        )


class DependencyReplacementReconciliationHandler(ProjectionAwareHandler):
    operation_kind = "dependency_replace"

    def reconcile(self, repository, state, claim, history, plan):
        payload = self._verify(state, plan)
        product = repository.get_product(state.tenant_id, state.environment, state.product_id)
        target_revision = int(payload.get("target_product_revision", -1))
        if product is None or product.revision < target_revision:
            return OperationReconciliationOutcome("retry", "product_pending", retryable=True)
        if product.revision > target_revision:
            return OperationReconciliationOutcome(
                "superseded", "newer_product_revision", error_code="newer_product_revision"
            )
        if product.etag != payload.get("target_product_etag"):
            raise OperationConsistencyError("dependency_product_diverged")
        snapshot = repository.read_complete_dependency_snapshot(
            state.tenant_id, state.environment, state.product_id, maximum=10_000
        )
        active = tuple(sorted(edge.upstream_product_id for edge in snapshot.dependencies if not edge.removed))
        if active != tuple(payload.get("upstream_product_ids", ())):
            return OperationReconciliationOutcome("retry", "dependency_edges_pending", retryable=True)
        result = self._existing_result(repository, state)
        return OperationReconciliationOutcome(
            "applied",
            "dependency_projection_verified",
            result.payload if result else {"revision": product.revision, "etag": product.etag},
        )


class ProductLifecycleReconciliationHandler(ProjectionAwareHandler):
    operation_kind = "product_lifecycle"

    def reconcile(self, repository, state, claim, history, plan):
        payload = self._verify(state, plan)
        product = repository.get_product(state.tenant_id, state.environment, state.product_id)
        target_revision = int(payload.get("target_revision", -1))
        if product is None or product.revision < target_revision:
            return OperationReconciliationOutcome("retry", "lifecycle_transition_pending", retryable=True)
        if product.revision > target_revision:
            return OperationReconciliationOutcome("superseded", error_code="newer_lifecycle_revision")
        if product.lifecycle_state != payload.get("target_lifecycle") or product.etag != payload.get("target_etag"):
            raise OperationConsistencyError("lifecycle_projection_diverged")
        result = self._existing_result(repository, state)
        return OperationReconciliationOutcome(
            "applied",
            "lifecycle_projection_verified",
            result.payload if result else {"revision": product.revision, "etag": product.etag},
        )


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
        concrete = (
            ManualMembershipReconciliationHandler(),
            ProposalAcceptReconciliationHandler(),
            ProposalRejectReconciliationHandler(),
            ProposalExpireReconciliationHandler(),
            ProposalSupersedeReconciliationHandler(),
            MembershipExclusionReconciliationHandler(),
            DependencyReplacementReconciliationHandler(),
            ProductLifecycleReconciliationHandler(),
        )
        self._handlers = {handler.operation_kind: handler for handler in concrete}
        if handlers:
            self._handlers.update(handlers)

    def get(self, operation_kind: str) -> OperationReconciliationHandler:
        try:
            return self._handlers[operation_kind]
        except KeyError as exc:
            raise OperationConsistencyError("unknown_operation_kind") from exc


def _checksum(payload: Mapping[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def persist_pending_operation(
    repository: DataProductRepository,
    *,
    tenant_id: str,
    environment: str,
    product_id: str,
    operation_id: str,
    operation_kind: str,
    idempotency_record_id: str,
    payload: Mapping[str, Any],
    created_at: Any,
) -> DataProductOperationState:
    """Persist immutable intent before creating its OCC-controlled pending state."""
    checksum = _checksum(payload)
    reference = f"plan:{operation_id}:{checksum}"
    repository.save_operation_plan(
        DataProductOperationPlan(
            reference, tenant_id, environment, product_id, operation_id, operation_kind, checksum, payload
        )
    )
    state = DataProductOperationState(
        operation_id,
        tenant_id,
        environment,
        product_id,
        operation_kind,
        "pending",
        0,
        created_at,
        plan_reference=reference,
        idempotency_record_id=idempotency_record_id,
    )
    repository.create_operation_state(state)
    return repository.get_operation_state(tenant_id, environment, operation_id) or state


class DataProductOperationService:
    """Independently runnable, CAS-fenced operation reconciliation service."""

    def __init__(
        self,
        repository: DataProductRepository,
        *,
        worker_id: str,
        claim_ttl_seconds: int = 30,
        max_attempts: int = 5,
        registry=None,
    ) -> None:
        self.repository = repository
        self.worker_id = worker_id
        self.claim_ttl_seconds = claim_ttl_seconds
        self.max_attempts = max_attempts
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
        if state.attempt_count >= self.max_attempts:
            self.repository.fail_operation(claim, error_code="reconciliation_attempts_exhausted")
            return "failed"
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
                terminal = DataProductOperationHistoryEvent(
                    f"terminal:{operation_id}:{checksum}",
                    operation_id,
                    tenant_id,
                    environment,
                    claimed.product_id,
                    claimed.operation_kind,
                    str(plan.payload.get("action", claimed.operation_kind)),
                    "applied",
                    str(plan.payload.get("actor", "reconciler")),
                    str(plan.payload.get("reason", "reconciliation")),
                    str(plan.payload["request_fingerprint"]),
                    utc_now(),
                    expected_revision=plan.payload.get("expected_revision"),
                    expected_etag=plan.payload.get("expected_etag"),
                    result_revision=int(payload.get("revision", 0)),
                    result_etag=str(payload.get("etag", "recovered")),
                    plan_checksum=plan.checksum,
                    result_checksum=result.checksum,
                    worker_id=self.worker_id,
                    applied_at=result.created_at,
                )
                self.repository.append_operation_history(terminal)
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

    def reconcile_batch(
        self, tenant_id: str, environment: str, *, limit: int = 100, operation_kind: str | None = None
    ) -> dict[str, int]:
        if not 1 <= limit <= 1000:
            raise ValueError("reconciliation limit outside bounds")
        outcomes = {"applied": 0, "superseded": 0, "failed": 0, "retry": 0, "missing": 0}
        for state in self.repository.list_reconcilable_operations(tenant_id, environment, limit=limit):
            if operation_kind is not None and state.operation_kind != operation_kind:
                continue
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
