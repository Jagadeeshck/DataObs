from __future__ import annotations

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import (
    DataProduct,
    DataProductDependencyPage,
    DataProductDependencyProjection,
    DataProductMembership,
    DataProductMembershipDecision,
    DataProductMembershipDecisionPage,
    DataProductMembershipPage,
    DataProductMembershipProposal,
    DataProductMembershipProposalPage,
    DataProductOperationResult,
    DataProductRevisionEvent,
)
from services.data_products.dependency_events import (
    DataProductDependencyMutationPlan,
    DataProductDependencyOperationResult,
    DataProductDependencyReadSnapshot,
    DependencyResultInconsistent,
)
from services.data_products.events import ProductConsistencyError
from services.data_products.idempotency import (
    DataProductIdempotencyRecord,
    IdempotencyConflict,
    IdempotencyReservationResult,
    IdempotencyReservationStatus,
)
from services.data_products.operation_state import (
    DataProductOperationCheckpoint,
    DataProductOperationClaim,
    DataProductOperationFinalResult,
    DataProductOperationHistoryEvent,
    DataProductOperationPlan,
    DataProductOperationResultEnvelope,
    DataProductOperationState,
    OperationClaimConflict,
)
from services.data_products.repository import ProductVersionConflict


class MemoryDataProductRepository:
    """Deterministic test repository; production composition must use Elasticsearch."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str, str], DataProduct] = {}
        self.revisions: dict[tuple[str, str, str, int], tuple[DataProduct, str, str]] = {}
        self.operations: dict[str, tuple[DataProductRevisionEvent, DataProduct]] = {}
        self.idempotency: dict[str, DataProductIdempotencyRecord] = {}
        self.memberships: dict[tuple[str, str, str, str], DataProductMembership] = {}
        self.proposals: dict[tuple[str, str, str, str, int], DataProductMembershipProposal] = {}
        self.decisions: dict[tuple[str, str, str, str], DataProductMembershipDecision] = {}
        self.dependencies: dict[tuple[str, str, str, str], DataProductDependencyProjection] = {}
        self.dependency_plans: dict[str, DataProductDependencyMutationPlan] = {}
        self.dependency_results: dict[str, DataProductDependencyOperationResult] = {}
        self.operation_states: dict[str, DataProductOperationState] = {}
        self.operation_history: dict[str, DataProductOperationHistoryEvent] = {}
        self.operation_plans: dict[tuple[str, str, str, str], DataProductOperationPlan] = {}
        self.operation_results: dict[tuple[str, str, str, str], DataProductOperationResultEnvelope] = {}

    def add_operation_state(self, state: DataProductOperationState) -> None:
        self.operation_states[state.operation_id] = state

    def create_operation_state(self, state: DataProductOperationState) -> None:
        existing = self.operation_states.get(state.operation_id)
        if existing is not None and existing != state:
            raise ProductConsistencyError("divergent operation state")
        self.operation_states[state.operation_id] = state

    def get_operation_state(self, tenant_id, environment, operation_id):
        state = self.operation_states.get(operation_id)
        return state if state and (state.tenant_id, state.environment) == (tenant_id, environment) else None

    def list_reconcilable_operations(self, tenant_id, environment, *, limit=100):
        values = [
            s
            for s in self.operation_states.values()
            if (s.tenant_id, s.environment) == (tenant_id, environment)
            and (
                s.status == "pending"
                or (s.status == "claimed" and s.claim_expires_at and s.claim_expires_at <= utc_now())
            )
        ]
        return sorted(values, key=lambda s: (s.updated_at, s.operation_id))[:limit]

    def claim_operation(
        self,
        tenant_id,
        environment,
        operation_id,
        *,
        worker_id,
        now,
        expires_at,
        expected_seq_no,
        expected_primary_term,
    ):
        state = self.get_operation_state(tenant_id, environment, operation_id)
        if state is None:
            raise KeyError(operation_id)
        if (state.seq_no, state.primary_term) != (expected_seq_no, expected_primary_term):
            raise OperationClaimConflict("operation_claim_conflict")
        if state.claim_expires_at and state.claim_expires_at > now and state.claim_owner != worker_id:
            raise OperationClaimConflict("operation_already_claimed")
        if state.status not in {"pending", "claimed"} or (
            state.status == "claimed" and (state.claim_expires_at is None or state.claim_expires_at > now)
        ):
            raise OperationClaimConflict("operation_not_reconcilable")
        claim = DataProductOperationClaim(
            operation_id,
            worker_id,
            state.claim_generation + 1,
            now,
            expires_at,
            tenant_id,
            environment,
            state.product_id,
        )
        self.operation_states[operation_id] = state.claimed(claim, now=now)
        return claim

    def _owned_state(self, claim):
        state = self.operation_states.get(claim.operation_id)
        if (
            state is None
            or (
                claim.tenant_id
                and (state.tenant_id, state.environment, state.product_id)
                != (claim.tenant_id, claim.environment, claim.product_id)
            )
            or (state.claim_owner, state.claim_generation) != (claim.owner, claim.generation)
            or state.claim_expires_at is None
            or state.claim_expires_at <= utc_now()
        ):
            raise OperationClaimConflict("stale_operation_claim")
        return state

    def renew_operation_claim(self, claim, *, expires_at):
        from dataclasses import replace

        state = self._owned_state(claim)
        renewed = replace(claim, expires_at=expires_at)
        self.operation_states[claim.operation_id] = replace(state, claim_expires_at=expires_at, seq_no=state.seq_no + 1)
        return renewed

    def checkpoint_operation(self, claim, checkpoint: DataProductOperationCheckpoint):
        from dataclasses import replace

        state = self._owned_state(claim)
        self.operation_states[claim.operation_id] = replace(
            state, last_checkpoint=checkpoint, updated_at=checkpoint.occurred_at, seq_no=state.seq_no + 1
        )

    def _finalize_state(self, claim, status, *, result=None, error_code=None):
        from dataclasses import replace

        state = self._owned_state(claim)
        when = result.applied_at if result else state.updated_at
        self.operation_states[claim.operation_id] = replace(
            state,
            status=status,
            result_reference=result.checksum if result else state.result_reference,
            last_error_code=error_code,
            claim_owner=None,
            claim_expires_at=None,
            updated_at=when,
            seq_no=state.seq_no + 1,
        )

    def complete_operation(self, claim, result: DataProductOperationFinalResult):
        self._finalize_state(claim, "applied", result=result)

    def supersede_operation(self, claim, *, error_code):
        self._finalize_state(claim, "superseded", error_code=error_code)

    def fail_operation(self, claim, *, error_code):
        self._finalize_state(claim, "failed", error_code=error_code)

    def append_operation_history(self, event: DataProductOperationHistoryEvent):
        existing = self.operation_history.get(event.event_id)
        if existing is not None and existing != event:
            raise ProductConsistencyError("divergent immutable operation history")
        self.operation_history[event.event_id] = event

    def get_operation_history(self, tenant_id, environment, operation_id, *, limit=100):
        values = [
            e
            for e in self.operation_history.values()
            if (e.tenant_id, e.environment, e.operation_id) == (tenant_id, environment, operation_id)
        ]
        return sorted(values, key=lambda e: (e.occurred_at, e.event_id))[:limit]

    def save_operation_plan(self, plan):
        key = (plan.tenant_id, plan.environment, plan.product_id, plan.operation_id)
        existing = self.operation_plans.get(key)
        if existing is not None and existing != plan:
            raise ProductConsistencyError("divergent operation plan")
        self.operation_plans[key] = plan

    def load_operation_plan(self, tenant_id, environment, product_id, operation_id):
        return self.operation_plans.get((tenant_id, environment, product_id, operation_id))

    def save_operation_result(self, result):
        key = (result.tenant_id, result.environment, result.product_id, result.operation_id)
        existing = self.operation_results.get(key)
        if existing is not None and existing != result:
            raise ProductConsistencyError("divergent operation result")
        self.operation_results[key] = result

    def load_operation_result(self, tenant_id, environment, product_id, operation_id):
        return self.operation_results.get((tenant_id, environment, product_id, operation_id))

    def repair_idempotency_completion(self, record_id, result):
        self.complete_idempotency(
            record_id,
            operation_id=self.idempotency[record_id].operation_id or "",
            revision=result.revision,
            etag=result.etag,
        )

    def reserve_idempotency(self, record_id: str, record: DataProductIdempotencyRecord) -> IdempotencyReservationResult:
        existing = self.idempotency.get(record_id)
        if existing:
            if existing.request_fingerprint != record.request_fingerprint:
                raise IdempotencyConflict("idempotency_conflict")
            return IdempotencyReservationResult(
                status=IdempotencyReservationStatus(f"existing_{existing.state}"),
                record=existing.model_copy(deep=True),
                immutable_result_ref=existing.operation_id,
            )
        self.idempotency[record_id] = record.model_copy(deep=True)
        return IdempotencyReservationResult(status=IdempotencyReservationStatus.CREATED, record=record)

    def complete_idempotency(self, record_id: str, *, operation_id: str, revision: int, etag: str) -> None:
        from packages.domain_model.base import utc_now

        record = self.idempotency[record_id]
        now = utc_now()
        self.idempotency[record_id] = record.model_copy(
            update={
                "operation_id": operation_id,
                "state": "completed",
                "result_revision": revision,
                "result_etag": etag,
                "completed_at": now,
                "updated_at": now,
            }
        )

    def get_idempotency(self, record_id: str):
        value = self.idempotency.get(record_id)
        return value.model_copy(deep=True) if value else None

    def _terminal_idempotency(self, record_id: str, state: str, error_code: str | None = None) -> None:
        from packages.domain_model.base import utc_now

        record = self.idempotency[record_id]
        if record.state == "completed":
            return
        now = utc_now()
        self.idempotency[record_id] = record.model_copy(
            update={"state": state, "error_code": error_code, "updated_at": now}
        )

    def fail_idempotency(self, record_id: str, *, error_code: str) -> None:
        self._terminal_idempotency(record_id, "failed", error_code)

    def supersede_idempotency(self, record_id: str, *, error_code: str = "newer_revision") -> None:
        self._terminal_idempotency(record_id, "superseded", error_code)

    def list_expired_idempotency(self, tenant_id: str, environment: str, *, now, limit: int = 100):
        return [
            value.model_copy(deep=True)
            for value in sorted(self.idempotency.values(), key=lambda item: (item.expires_at, item.resource_id))
            if (value.tenant_id, value.environment) == (tenant_id, environment) and value.expires_at <= now
        ][:limit]

    def get_product_revision(self, tenant_id: str, environment: str, product_id: str, revision: int):
        value = self.revisions.get((tenant_id, environment, product_id, revision))
        return value[0].model_copy(deep=True) if value else None

    def get_products_by_ids(self, tenant_id: str, environment: str, product_ids):
        if len(set(product_ids)) > 10_000:
            raise ValueError("product_id_count_exceeded")
        return [
            self.items[(tenant_id, environment, product_id)].model_copy(deep=True)
            for product_id in sorted(set(product_ids))
            if (tenant_id, environment, product_id) in self.items
        ]

    def get_operation(self, tenant_id: str, environment: str, operation_id: str):
        found = self.operations.get(operation_id)
        if found and (found[0].tenant_id, found[0].environment) == (tenant_id, environment):
            return found[0].model_copy(deep=True)
        return None

    def get_operation_result(
        self, tenant_id: str, environment: str, operation_id: str, expected_revision: int, expected_etag: str
    ) -> DataProductOperationResult:
        found = self.operations.get(operation_id)
        if not found or (found[0].tenant_id, found[0].environment) != (tenant_id, environment):
            raise ProductConsistencyError("immutable operation result missing")
        event, product = found
        if event.outcome != "applied" or event.revision != expected_revision or event.etag != expected_etag:
            raise ProductConsistencyError("immutable operation result diverged")
        return DataProductOperationResult(
            product=product.model_copy(deep=True),
            **event.model_dump(exclude={"product_id", "tenant_id", "environment", "error_code"}),
        )

    def list_pending_operations(
        self, tenant_id: str, environment: str, *, product_id=None, limit=100, include_applied=False
    ):
        values = [
            event
            for event, _ in self.operations.values()
            if (event.tenant_id, event.environment) == (tenant_id, environment)
            and (product_id is None or event.product_id == product_id)
            and (include_applied or event.outcome == "pending")
        ]
        return [
            value.model_copy(deep=True)
            for value in sorted(values, key=lambda x: (x.occurred_at, x.operation_id))[:limit]
        ]

    def list_revisions(self, tenant_id: str, environment: str, product_id: str, *, limit=100, search_after=None):
        values = [
            event
            for event, _ in self.operations.values()
            if (event.tenant_id, event.environment, event.product_id) == (tenant_id, environment, product_id)
        ]
        values.sort(key=lambda x: (x.revision, x.operation_id), reverse=True)
        if search_after:
            values = [v for v in values if (v.revision, v.operation_id) < tuple(search_after)]
        return [v.model_copy(deep=True) for v in values[:limit]]

    def begin_operation(self, event: DataProductRevisionEvent, product: DataProduct) -> DataProductRevisionEvent:
        existing = self.operations.get(event.operation_id)
        if existing:
            if existing[0].definition_checksum != event.definition_checksum:
                raise ProductConsistencyError("divergent operation replay")
            return existing[0].model_copy(deep=True)
        revision_key = (event.tenant_id, event.environment, event.product_id, event.revision)
        for saved_event, _ in self.operations.values():
            if (
                saved_event.tenant_id,
                saved_event.environment,
                saved_event.product_id,
                saved_event.revision,
            ) == revision_key and saved_event.definition_checksum != event.definition_checksum:
                raise ProductConsistencyError("divergent same-revision checksum")
        self.operations[event.operation_id] = (event.model_copy(deep=True), product.model_copy(deep=True))
        return event

    def begin_dependency_operation(self, event, product, plan):
        saved = self.begin_operation(event, product)
        existing = self.dependency_plans.get(event.operation_id)
        if existing is not None and existing != plan:
            raise ProductConsistencyError("divergent dependency operation plan")
        self.dependency_plans[event.operation_id] = plan
        return saved

    def load_dependency_operation_plan(self, tenant_id, environment, operation_id):
        found = self.operations.get(operation_id)
        plan = self.dependency_plans.get(operation_id)
        if not found or plan is None or (found[0].tenant_id, found[0].environment) != (tenant_id, environment):
            return None
        return found[0].model_copy(deep=True), found[1].model_copy(deep=True), plan

    def save_dependency_operation_result(self, result):
        operation_id = result.operation.operation_id
        existing = self.dependency_results.get(operation_id)
        if existing is not None and existing != result:
            raise DependencyResultInconsistent("dependency_result_inconsistent")
        self.dependency_results[operation_id] = result

    def get_dependency_operation_result(self, tenant_id, environment, product_id, operation_id):
        result = self.dependency_results.get(operation_id)
        if result is None or (
            result.operation.tenant_id,
            result.operation.environment,
            result.operation.product_id,
        ) != (tenant_id, environment, product_id):
            raise DependencyResultInconsistent("dependency_result_inconsistent")
        return result

    def finish_operation(self, event: DataProductRevisionEvent) -> None:
        existing = self.operations.get(event.operation_id)
        if not existing or existing[0].definition_checksum != event.definition_checksum:
            raise ProductConsistencyError("operation outcome has no matching pending operation")
        self.operations[event.operation_id] = (event.model_copy(deep=True), existing[1])
        product = existing[1]
        self.revisions[(event.tenant_id, event.environment, event.product_id, event.revision)] = (
            product.model_copy(deep=True),
            event.actor,
            event.reason,
        )

    def create_product(self, product: DataProduct) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        if key in self.items:
            raise ProductVersionConflict("data product exists")
        self.items[key] = product.model_copy(deep=True)
        return product

    def get_product(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None:
        item = self.items.get((tenant_id, environment, product_id))
        return item.model_copy(deep=True) if item else None

    def list_products(
        self, tenant_id: str, environment: str, *, limit: int, search_after=None, **_
    ) -> list[DataProduct]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        values = sorted(
            (p for (t, e, _), p in self.items.items() if (t, e) == (tenant_id, environment)), key=lambda p: p.id
        )
        if search_after:
            values = [p for p in values if p.id > str(search_after[0])]
        return [p.model_copy(deep=True) for p in values[:limit]]

    def update_product(self, product: DataProduct, *, expected_etag: str) -> DataProduct:
        key = (product.tenant_id, product.environment, product.id)
        current = self.items.get(key)
        if current is None:
            raise KeyError(product.id)
        if current.etag != expected_etag:
            raise ProductVersionConflict("stale data product ETag")
        self.items[key] = product.model_copy(deep=True)
        return product

    def append_revision(self, product: DataProduct, *, actor: str, reason: str) -> None:
        key = (product.tenant_id, product.environment, product.id, product.revision)
        existing = self.revisions.get(key)
        event = (product.model_copy(deep=True), actor, reason)
        if existing:
            if existing[0].model_dump(mode="json") == event[0].model_dump(mode="json") and existing[1:] == event[1:]:
                return
            raise ProductVersionConflict("divergent data product revision")
        self.revisions[key] = event

    def create_membership(
        self, tenant_id: str, environment: str, membership: DataProductMembership, *, create_only: bool = True
    ) -> DataProductMembership:
        if (tenant_id, environment) != (membership.tenant_id, membership.environment):
            raise ValueError("membership scope mismatch")
        key = (tenant_id, environment, membership.product_id, membership.membership_id)
        current = self.memberships.get(key)
        if current and current != membership:
            raise ProductVersionConflict("divergent membership replay")
        self.memberships[key] = membership.model_copy(deep=True)
        return membership.model_copy(deep=True)

    def get_membership(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> DataProductMembership | None:
        value = self.memberships.get((tenant_id, environment, product_id, membership_id))
        return value.model_copy(deep=True) if value else None

    def list_memberships(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 50, search_after=None
    ) -> DataProductMembershipPage:
        values = sorted(
            (v for k, v in self.memberships.items() if k[:3] == (tenant_id, environment, product_id)),
            key=lambda v: (-v.updated_at.timestamp(), v.membership_id),
        )
        return DataProductMembershipPage(
            items=[v.model_copy(deep=True) for v in values[:limit]], has_more=len(values) > limit
        )

    def exclude_membership(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        membership_id: str,
        *,
        actor: str,
        reason: str,
        expected_etag: str,
    ) -> DataProductMembership:
        from hashlib import sha256

        from packages.domain_model.base import utc_now

        current = self.get_membership(tenant_id, environment, product_id, membership_id)
        if not current:
            raise KeyError(membership_id)
        if current.etag != expected_etag:
            raise ProductVersionConflict("stale membership ETag")
        now = utc_now()
        updated = current.model_copy(
            update={
                "state": "excluded",
                "excluded_at": now,
                "excluded_by": actor,
                "exclusion_reason": reason,
                "updated_at": now,
                "revision": current.revision + 1,
                "etag": sha256(f"{current.etag}:excluded".encode()).hexdigest(),
            }
        )
        self.memberships[(tenant_id, environment, product_id, membership_id)] = updated
        return updated.model_copy(deep=True)

    def create_membership_proposal(self, proposal: DataProductMembershipProposal) -> DataProductMembershipProposal:
        key = (
            proposal.tenant_id,
            proposal.environment,
            proposal.product_id,
            proposal.proposal_id,
            proposal.proposal_revision,
        )
        current = self.proposals.get(key)
        if current and current != proposal:
            raise ProductVersionConflict("divergent proposal replay")
        self.proposals[key] = proposal.model_copy(deep=True)
        return proposal.model_copy(deep=True)

    def get_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal | None:
        values = [v for k, v in self.proposals.items() if k[:4] == (tenant_id, environment, product_id, proposal_id)]
        return max(values, key=lambda v: v.proposal_revision).model_copy(deep=True) if values else None

    def list_membership_proposals(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 50, search_after=None
    ) -> DataProductMembershipProposalPage:
        values = sorted(
            (v for k, v in self.proposals.items() if k[:3] == (tenant_id, environment, product_id)),
            key=lambda v: (v.created_at, v.proposal_revision),
            reverse=True,
        )
        return DataProductMembershipProposalPage(
            items=[v.model_copy(deep=True) for v in values[:limit]], has_more=len(values) > limit
        )

    def _transition_membership_proposal(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        proposal_id: str,
        state: str,
        *,
        expected_revision: int | None = None,
    ) -> DataProductMembershipProposal:
        current = self.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
        if current is None:
            raise KeyError(proposal_id)
        if expected_revision is not None and current.proposal_revision != expected_revision:
            raise ProductVersionConflict("proposal_revision_conflict")
        if current.state != "proposed":
            raise ProductVersionConflict(f"proposal_already_{current.state}")
        updated = current.model_copy(update={"state": state})
        self.proposals[(tenant_id, environment, product_id, proposal_id, current.proposal_revision)] = updated
        return updated.model_copy(deep=True)

    def accept_membership_proposal(self, *args, **kwargs):
        return self._transition_membership_proposal(*args, "accepted", **kwargs)

    def reject_membership_proposal(self, *args, **kwargs):
        return self._transition_membership_proposal(*args, "rejected", **kwargs)

    def expire_membership_proposal(self, *args, **kwargs):
        return self._transition_membership_proposal(*args, "expired", **kwargs)

    def supersede_membership_proposal(self, *args, **kwargs):
        return self._transition_membership_proposal(*args, "superseded", **kwargs)

    def append_membership_decision(
        self, tenant_id: str, environment: str, product_id: str, decision: DataProductMembershipDecision
    ) -> DataProductMembershipDecision:
        key = (tenant_id, environment, product_id, decision.decision_id)
        current = self.decisions.get(key)
        if current and current != decision:
            raise ProductConsistencyError("divergent decision replay")
        self.decisions[key] = decision.model_copy(deep=True)
        return decision.model_copy(deep=True)

    def get_membership_decision(self, tenant_id, environment, product_id, decision_id):
        value = self.decisions.get((tenant_id, environment, product_id, decision_id))
        return value.model_copy(deep=True) if value else None

    def get_membership_decisions_for_operation(self, tenant_id, environment, product_id, operation_id):
        return tuple(
            value.model_copy(deep=True)
            for key, value in sorted(self.decisions.items())
            if key[:3] == (tenant_id, environment, product_id) and value.operation_id == operation_id
        )

    def list_membership_decisions(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 50, search_after=None
    ) -> DataProductMembershipDecisionPage:
        values = sorted(
            (v for k, v in self.decisions.items() if k[:3] == (tenant_id, environment, product_id)),
            key=lambda v: (v.decided_at, v.decision_id),
            reverse=True,
        )
        return DataProductMembershipDecisionPage(
            items=[v.model_copy(deep=True) for v in values[:limit]], has_more=len(values) > limit
        )

    def save_dependencies(
        self, tenant_id: str, environment: str, product_id: str, dependencies: list[DataProductDependencyProjection]
    ) -> DataProductDependencyPage:
        from packages.domain_model.base import utc_now

        proposed = {d.upstream_product_id: d for d in dependencies}
        now = utc_now()
        for key, edge in list(self.dependencies.items()):
            if key[:3] == (tenant_id, environment, product_id) and key[3] not in proposed and not edge.removed:
                self.dependencies[key] = edge.model_copy(
                    update={
                        "removed": True,
                        "removed_at": now,
                        "removed_by_revision": max(
                            (d.product_revision for d in dependencies), default=edge.product_revision + 1
                        ),
                        "updated_at": now,
                    }
                )
        for edge in dependencies:
            self.dependencies[(tenant_id, environment, product_id, edge.upstream_product_id)] = edge.model_copy(
                deep=True
            )
        return self.list_dependencies(tenant_id, environment, product_id)

    def read_complete_dependency_snapshot(self, tenant_id, environment, product_id, *, maximum):
        values = sorted(
            (
                v.model_copy(deep=True)
                for k, v in self.dependencies.items()
                if k[:3] == (tenant_id, environment, product_id)
            ),
            key=lambda value: (value.removed, value.upstream_product_id, value.graph_version),
        )
        if len(values) > maximum:
            raise ValueError("dependency_snapshot_maximum_exceeded")
        return DataProductDependencyReadSnapshot(tuple(values), len(values), True)

    def apply_dependency_mutation_plan(self, tenant_id, environment, product_id, plan):
        # The product OCC token has already been acquired. Each target comparison is
        # idempotent, making a retry safe after any edge boundary.
        for edge in (*plan.upserts, *plan.tombstones):
            key = (tenant_id, environment, product_id, edge.upstream_product_id)
            current = self.dependencies.get(key)
            if current == edge:
                continue
            self.dependencies[key] = edge.model_copy(deep=True)
        return self.list_dependencies(tenant_id, environment, product_id, limit=max(1, len(self.dependencies)))

    def list_dependencies(
        self, tenant_id: str, environment: str, product_id: str, *, limit: int = 50, search_after=None
    ) -> DataProductDependencyPage:
        values = sorted(
            (v for k, v in self.dependencies.items() if k[:3] == (tenant_id, environment, product_id)),
            key=lambda v: (v.removed, v.upstream_product_id, v.graph_version),
        )
        return DataProductDependencyPage(
            items=[v.model_copy(deep=True) for v in values[:limit]], has_more=len(values) > limit
        )
