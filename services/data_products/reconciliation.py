from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from typing import Any, Literal, Protocol

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductMembership, DataProductRevisionEvent
from services.data_products.operation_state import (
    DataProductOperationCheckpoint,
    DataProductOperationClaim,
    DataProductOperationFinalResult,
    DataProductOperationHistoryEvent,
    DataProductOperationPlan,
    DataProductOperationReconciliationResult,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
    OperationClaimConflict,
    OperationConsistencyError,
    ReconciliationStatus,
)
from services.data_products.repository import DataProductRepository


@dataclass
class OperationReconciliationContext:
    """Claim-fenced capabilities exposed to concrete repair handlers."""

    claim: DataProductOperationClaim
    assert_owned_callback: Callable[[DataProductOperationClaim], None]
    renew_callback: Callable[[DataProductOperationClaim], DataProductOperationClaim]
    checkpoint_callback: Callable[[DataProductOperationClaim, str, str], None]

    def assert_owned(self) -> None:
        self.assert_owned_callback(self.claim)

    def renew_if_needed(self) -> DataProductOperationClaim:
        self.claim = self.renew_callback(self.claim)
        return self.claim

    def checkpoint(self, name: str, checksum: str) -> None:
        self.assert_owned()
        self.checkpoint_callback(self.claim, name, checksum)


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
            target = payload.get("membership_target")
            if not isinstance(target, Mapping):
                raise OperationConsistencyError("manual_membership_plan_incomplete")
            candidate = DataProductMembership.model_validate(target)
            if (
                candidate.tenant_id,
                candidate.environment,
                candidate.product_id,
                candidate.membership_id,
            ) != (state.tenant_id, state.environment, state.product_id, payload.get("membership_id")):
                raise OperationConsistencyError("manual_membership_plan_poisoned")
            membership = repository.create_membership(state.tenant_id, state.environment, candidate)
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
        self._handlers: dict[str, OperationReconciliationHandler] = {
            handler.operation_kind: handler for handler in concrete
        }
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


class RecoverableDataProductOperationCoordinator:
    """Shared entry point for durable operation creation and recovery.

    Mutation services use ``begin`` before touching a projection and delegate an
    existing pending reservation to ``reconcile_pending``. Terminal methods are
    intentionally claim-fenced by ``DataProductOperationService``.
    """

    def __init__(self, repository: DataProductRepository, operation_service: "DataProductOperationService") -> None:
        self.repository = repository
        self.operation_service = operation_service

    def begin(self, **operation: Any) -> DataProductOperationState:
        return persist_pending_operation(self.repository, **operation)

    def checkpoint(self, claim: DataProductOperationClaim, name: str, checksum: str) -> None:
        self.repository.checkpoint_operation(claim, DataProductOperationCheckpoint(name, checksum, utc_now()))

    def complete(self, claim: DataProductOperationClaim, result: DataProductOperationFinalResult) -> None:
        self.repository.complete_operation(claim, result)

    def fail(self, claim: DataProductOperationClaim, error_code: str) -> None:
        self.repository.fail_operation(claim, error_code=error_code)

    def supersede(self, claim: DataProductOperationClaim, error_code: str) -> None:
        self.repository.supersede_operation(claim, error_code=error_code)

    def reconcile_pending(
        self, tenant_id: str, environment: str, operation_id: str
    ) -> DataProductOperationReconciliationResult:
        return self.operation_service.reconcile_operation(tenant_id, environment, operation_id)


class DataProductOperationService:
    """Independently runnable, CAS-fenced operation reconciliation service."""

    def __init__(
        self,
        repository: DataProductRepository,
        *,
        worker_id: str,
        claim_ttl_seconds: int = 30,
        claim_renewal_window_seconds: int = 10,
        max_attempts: int = 5,
        registry=None,
    ) -> None:
        self.repository = repository
        self.worker_id = worker_id
        self.claim_ttl_seconds = claim_ttl_seconds
        if claim_renewal_window_seconds < 0 or claim_renewal_window_seconds >= claim_ttl_seconds:
            raise ValueError("claim renewal window must be non-negative and less than claim TTL")
        self.claim_renewal_window_seconds = claim_renewal_window_seconds
        self.max_attempts = max_attempts
        self.registry = registry or OperationReconciliationRegistry()

    def get_operation_status(self, tenant_id: str, environment: str, operation_id: str):
        return self.repository.get_operation_state(tenant_id, environment, operation_id)

    def _result(
        self,
        operation_id: str,
        status: ReconciliationStatus,
        state: DataProductOperationState | None,
        *,
        recovered: bool = False,
        retryable: bool = False,
        error_code: str | None = None,
    ) -> DataProductOperationReconciliationResult:
        return DataProductOperationReconciliationResult(
            operation_id=operation_id,
            operation_kind=state.operation_kind if state else None,
            status=status,
            replayed=bool(state and state.status in {"applied", "superseded", "failed"}),
            recovered=recovered,
            retryable=retryable,
            attempt_count=state.attempt_count if state else 0,
            claim_generation=state.claim_generation if state else 0,
            last_checkpoint=state.last_checkpoint.name if state and state.last_checkpoint else None,
            result_reference=state.result_reference if state else None,
            error_code=error_code or (state.last_error_code if state else None),
            retry_after_seconds=self.claim_ttl_seconds if retryable else None,
        )

    def _renew_if_needed(self, claim: DataProductOperationClaim) -> DataProductOperationClaim:
        now = utc_now()
        if claim.expires_at - now <= timedelta(seconds=self.claim_renewal_window_seconds):
            return self.repository.renew_operation_claim(
                claim, expires_at=now + timedelta(seconds=self.claim_ttl_seconds)
            )
        return claim

    def reconcile_operation(
        self, tenant_id: str, environment: str, operation_id: str
    ) -> DataProductOperationReconciliationResult:
        state = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if state is None:
            return self._result(operation_id, "missing", None)
        if state.status in {"applied", "superseded", "failed"}:
            self._repair_terminal_revisit(state)
            return self._result(operation_id, state.status, state)
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
            return self._result(operation_id, "retry", state, retryable=True)
        claimed = self.repository.get_operation_state(tenant_id, environment, operation_id)
        if claimed is None:
            return self._result(operation_id, "missing", None)
        # Claiming increments the attempt. Check the claimed generation, not the
        # stale pre-claim document; this prevents an off-by-one extra attempt.
        if claimed.attempt_count >= self.max_attempts:
            self.repository.fail_operation(claim, error_code="reconciliation_attempts_exhausted")
            final = self.repository.get_operation_state(tenant_id, environment, operation_id)
            return self._result(operation_id, "failed", final, error_code="reconciliation_attempts_exhausted")
        plan = self.repository.load_operation_plan(tenant_id, environment, claimed.product_id, operation_id)
        if plan is None:
            self.repository.fail_operation(claim, error_code="operation_plan_missing")
            final = self.repository.get_operation_state(tenant_id, environment, operation_id)
            return self._result(operation_id, "failed", final, error_code="operation_plan_missing")
        history = self.repository.get_operation_history(tenant_id, environment, operation_id)
        try:
            outcome = self.registry.get(claimed.operation_kind).reconcile(
                self.repository, claimed, claim, history, plan
            )
            if outcome.status == "retry":
                current = self.repository.get_operation_state(tenant_id, environment, operation_id)
                return self._result(operation_id, "retry", current, retryable=True, error_code=outcome.error_code)
            claim = self._renew_if_needed(claim)
            checkpoint_name = outcome.checkpoint or "projections_verified"
            checkpoint = DataProductOperationCheckpoint(checkpoint_name, plan.checksum, utc_now())
            self.repository.checkpoint_operation(claim, checkpoint)
            if outcome.status == "applied":
                payload = outcome.final_result or {}
                checksum = _checksum(payload)
                result = self.repository.load_operation_result(tenant_id, environment, claimed.product_id, operation_id)
                if result is not None:
                    if result.checksum != checksum or dict(result.payload) != dict(payload):
                        raise OperationConsistencyError("operation_result_mismatch")
                else:
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
                # Ownership is checked immediately before each owner-sensitive
                # terminal boundary. An immutable result may be replayed, but a
                # stale generation can never author terminal evidence or state.
                claim = self._renew_if_needed(claim)
                self.repository.checkpoint_operation(
                    claim, DataProductOperationCheckpoint("result_ready", result.checksum, utc_now())
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
                existing_terminal = next((event for event in history if event.event_id == terminal.event_id), None)
                if existing_terminal is None:
                    self.repository.append_operation_history(terminal)
                elif (
                    existing_terminal.outcome != "applied"
                    or existing_terminal.plan_checksum != plan.checksum
                    or existing_terminal.result_checksum != result.checksum
                ):
                    raise OperationConsistencyError("terminal_history_mismatch")
                final_result = DataProductOperationFinalResult(
                    int(payload.get("revision", 0)),
                    str(payload.get("etag", "recovered")),
                    result.reference,
                    result.created_at,
                )
                if claimed.idempotency_record_id:
                    self.repository.repair_idempotency_terminal(
                        claimed.idempotency_record_id,
                        claimed.operation_id,
                        str(plan.payload["request_fingerprint"]),
                        "completed",
                        final_result,
                    )
                # Mutable state is deliberately last: a takeover can repair all
                # earlier immutable/idempotency boundaries after a lost response.
                self.repository.complete_operation(claim, final_result)
                final = self.repository.get_operation_state(tenant_id, environment, operation_id)
                return self._result(operation_id, "applied", final, recovered=True)
            if outcome.status == "superseded":
                self._append_terminal_history(claimed, plan, outcome, "superseded")
                if claimed.idempotency_record_id:
                    self.repository.repair_idempotency_terminal(
                        claimed.idempotency_record_id,
                        claimed.operation_id,
                        str(plan.payload["request_fingerprint"]),
                        "superseded",
                        outcome.error_code or "newer_operation",
                    )
                self.repository.supersede_operation(claim, error_code=outcome.error_code or "newer_operation")
                final = self.repository.get_operation_state(tenant_id, environment, operation_id)
                return self._result(operation_id, "superseded", final, recovered=True)
            self._append_terminal_history(claimed, plan, outcome, "failed")
            if claimed.idempotency_record_id:
                self.repository.repair_idempotency_terminal(
                    claimed.idempotency_record_id,
                    claimed.operation_id,
                    str(plan.payload["request_fingerprint"]),
                    "failed",
                    outcome.error_code or "reconciliation_failed",
                )
            self.repository.fail_operation(claim, error_code=outcome.error_code or "reconciliation_failed")
            final = self.repository.get_operation_state(tenant_id, environment, operation_id)
            return self._result(operation_id, "failed", final, recovered=True)
        except OperationClaimConflict:
            current = self.repository.get_operation_state(tenant_id, environment, operation_id)
            return self._result(operation_id, "retry", current, retryable=True)
        except OperationConsistencyError as exc:
            try:
                self._append_terminal_history(
                    claimed,
                    plan,
                    OperationReconciliationOutcome("failed", error_code=exc.code),
                    "failed",
                )
                if claimed.idempotency_record_id:
                    self.repository.repair_idempotency_terminal(
                        claimed.idempotency_record_id,
                        claimed.operation_id,
                        str(plan.payload["request_fingerprint"]),
                        "failed",
                        exc.code,
                    )
                self.repository.fail_operation(claim, error_code=exc.code)
            except OperationClaimConflict:
                current = self.repository.get_operation_state(tenant_id, environment, operation_id)
                return self._result(operation_id, "retry", current, retryable=True)
            final = self.repository.get_operation_state(tenant_id, environment, operation_id)
            return self._result(operation_id, "failed", final, error_code=exc.code)

    def _repair_terminal_revisit(self, state: DataProductOperationState) -> None:
        """Validate immutable terminal evidence and repair its scoped reservation."""
        if not state.idempotency_record_id:
            return
        plan = self.repository.load_operation_plan(
            state.tenant_id, state.environment, state.product_id, state.operation_id
        )
        if plan is None or plan.reference != state.plan_reference or _checksum(plan.payload) != plan.checksum:
            raise OperationConsistencyError("operation_plan_mismatch")
        fingerprint = str(plan.payload.get("request_fingerprint", ""))
        if not fingerprint:
            raise OperationConsistencyError("operation_fingerprint_missing")
        terminal = [
            event
            for event in self.repository.get_operation_history(state.tenant_id, state.environment, state.operation_id)
            if event.outcome == state.status
        ]
        if not terminal:
            raise OperationConsistencyError("terminal_history_missing")
        event = terminal[-1]
        if event.operation_kind != state.operation_kind or event.plan_checksum != plan.checksum:
            raise OperationConsistencyError("terminal_history_mismatch")
        if state.status == "applied":
            result = self.repository.load_operation_result(
                state.tenant_id, state.environment, state.product_id, state.operation_id
            )
            if result is None or result.reference != state.result_reference or result.checksum != event.result_checksum:
                raise OperationConsistencyError("operation_result_mismatch")
            evidence: DataProductOperationFinalResult | str = DataProductOperationFinalResult(
                int(result.payload.get("revision", 0)),
                str(result.payload.get("etag", "")),
                result.reference,
                result.created_at,
            )
            outcome = "completed"
        else:
            evidence = event.error_code or state.last_error_code or f"reconciliation_{state.status}"
            outcome = state.status
        self.repository.repair_idempotency_terminal(
            state.idempotency_record_id,
            state.operation_id,
            fingerprint,
            outcome,
            evidence,
        )

    def _append_terminal_history(
        self,
        state: DataProductOperationState,
        plan: DataProductOperationPlan,
        outcome: OperationReconciliationOutcome,
        status: Literal["superseded", "failed"],
    ) -> None:
        error = outcome.error_code or f"reconciliation_{status}"
        event_id = f"terminal:{state.operation_id}:{status}:{plan.checksum}"
        existing = next(
            (
                event
                for event in self.repository.get_operation_history(
                    state.tenant_id, state.environment, state.operation_id
                )
                if event.event_id == event_id
            ),
            None,
        )
        if existing is not None:
            if existing.outcome != status or existing.error_code != error or existing.plan_checksum != plan.checksum:
                raise OperationConsistencyError("terminal_history_mismatch")
            return
        self.repository.append_operation_history(
            DataProductOperationHistoryEvent(
                event_id,
                state.operation_id,
                state.tenant_id,
                state.environment,
                state.product_id,
                state.operation_kind,
                str(plan.payload.get("action", state.operation_kind)),
                status,
                str(plan.payload.get("actor", "reconciler")),
                str(plan.payload.get("reason", "reconciliation")),
                str(plan.payload["request_fingerprint"]),
                utc_now(),
                plan_checksum=plan.checksum,
                error_code=error,
                worker_id=self.worker_id,
            )
        )

    def reconcile_batch(
        self, tenant_id: str, environment: str, *, limit: int = 100, operation_kind: str | None = None
    ) -> dict[str, int]:
        if not 1 <= limit <= 1000:
            raise ValueError("reconciliation limit outside bounds")
        outcomes = {"applied": 0, "superseded": 0, "failed": 0, "retry": 0, "missing": 0}
        for state in self.repository.list_reconcilable_operations(
            tenant_id, environment, limit=limit, operation_kind=operation_kind
        ):
            outcome = self.reconcile_operation(tenant_id, environment, state.operation_id)
            outcomes[outcome.status] = outcomes.get(outcome.status, 0) + 1
        return outcomes


OperationReconciler = DataProductOperationService


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
