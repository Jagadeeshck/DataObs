from __future__ import annotations

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
from services.data_products.events import ProductConsistencyError
from services.data_products.idempotency import (
    DataProductIdempotencyRecord,
    IdempotencyConflict,
    IdempotencyReservationResult,
    IdempotencyReservationStatus,
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
        return DataProductOperationResult(product=product.model_copy(deep=True), **event.model_dump())

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

    def append_membership_decision(
        self, tenant_id: str, environment: str, product_id: str, decision: DataProductMembershipDecision
    ) -> DataProductMembershipDecision:
        key = (tenant_id, environment, product_id, decision.decision_id)
        current = self.decisions.get(key)
        if current and current != decision:
            raise ProductConsistencyError("divergent decision replay")
        self.decisions[key] = decision.model_copy(deep=True)
        return decision.model_copy(deep=True)

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
