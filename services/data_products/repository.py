"""Authoritative, scope-explicit Data Product persistence contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, Sequence, TypeAlias

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
    DataProductSLODefinition,
    DataProductSLOEvaluation,
)
from services.data_products.idempotency import DataProductIdempotencyRecord, IdempotencyReservationResult


class ProductVersionConflict(RuntimeError):
    pass


SearchAfter: TypeAlias = Sequence[str | int | float]


@dataclass(frozen=True)
class DataProductListOptions:
    limit: int = 50
    search_after: SearchAfter | None = None


class DataProductRevisionListOptions(DataProductListOptions):
    pass


class DataProductMembershipListOptions(DataProductListOptions):
    pass


class DataProductProposalListOptions(DataProductListOptions):
    pass


class DataProductDecisionListOptions(DataProductListOptions):
    pass


class DataProductDependencyListOptions(DataProductListOptions):
    pass


@dataclass(frozen=True)
class DataProductMembershipMutationResult:
    membership: DataProductMembership
    operation_id: str
    replayed: bool = False
    decision_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataProductProposalDecisionResult:
    proposal: DataProductMembershipProposal
    membership: DataProductMembership | None
    operation_id: str
    replayed: bool = False


@dataclass(frozen=True)
class DataProductDependencyMutationResult:
    page: DataProductDependencyPage
    operation_id: str
    replayed: bool = False


@dataclass(frozen=True)
class DataProductReconciliationResult:
    operation_id: str
    outcome: str
    repaired_idempotency: bool


class DataProductRepository(Protocol):
    def reserve_idempotency(
        self, record_id: str, record: DataProductIdempotencyRecord
    ) -> IdempotencyReservationResult: ...
    def get_idempotency(self, record_id: str) -> DataProductIdempotencyRecord | None: ...
    def complete_idempotency(self, record_id: str, *, operation_id: str, revision: int, etag: str) -> None: ...
    def fail_idempotency(self, record_id: str, *, error_code: str) -> None: ...
    def supersede_idempotency(self, record_id: str, *, error_code: str = "newer_revision") -> None: ...
    def list_expired_idempotency(
        self, tenant_id: str, environment: str, *, now: datetime, limit: int = 100
    ) -> Sequence[DataProductIdempotencyRecord]: ...

    # Every lookup takes trusted scope, even where the document also carries it.
    def create_product(self, product: DataProduct) -> DataProduct: ...
    def get_product(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None: ...
    def get_product_revision(
        self, tenant_id: str, environment: str, product_id: str, revision: int
    ) -> DataProduct | None: ...
    def get_operation_result(
        self, tenant_id: str, environment: str, operation_id: str, expected_revision: int, expected_etag: str
    ) -> DataProductOperationResult: ...
    def list_products(self, tenant_id: str, environment: str, **options: Any) -> Sequence[DataProduct]: ...
    def update_product(self, product: DataProduct, *, expected_etag: str) -> DataProduct: ...
    def activate_product(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> DataProduct: ...
    def deprecate_product(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> DataProduct: ...
    def archive_product(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> DataProduct: ...

    def begin_operation(self, event: DataProductRevisionEvent, product: DataProduct) -> DataProductRevisionEvent: ...
    def get_operation(self, tenant_id: str, environment: str, operation_id: str) -> DataProductRevisionEvent | None: ...
    def finish_operation(self, event: DataProductRevisionEvent) -> None: ...
    def list_pending_operations(self, tenant_id: str, environment: str, **options: Any) -> Sequence[Any]: ...
    def append_revision(self, product: DataProduct, *, actor: str, reason: str) -> None: ...
    def list_revisions(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Sequence[Any]: ...
    def reconcile_pending_operations(self, tenant_id: str, environment: str, **options: Any) -> Sequence[Any]: ...

    def create_membership(
        self, tenant_id: str, environment: str, membership: DataProductMembership, **options: Any
    ) -> DataProductMembership: ...
    def get_membership(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> DataProductMembership | None: ...
    def list_memberships(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> DataProductMembershipPage: ...
    def exclude_membership(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str, **options: Any
    ) -> DataProductMembership: ...
    def create_membership_proposal(
        self, proposal: DataProductMembershipProposal, **options: Any
    ) -> DataProductMembershipProposal: ...
    def get_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal | None: ...
    def list_membership_proposals(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> DataProductMembershipProposalPage: ...
    def accept_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options: Any
    ) -> Any: ...
    def reject_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options: Any
    ) -> Any: ...
    def expire_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options: Any
    ) -> Any: ...
    def supersede_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options: Any
    ) -> Any: ...
    def append_membership_decision(
        self, tenant_id: str, environment: str, product_id: str, decision: DataProductMembershipDecision, **options: Any
    ) -> Any: ...
    def list_membership_decisions(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> DataProductMembershipDecisionPage: ...

    def save_dependencies(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        dependencies: Sequence[DataProductDependencyProjection],
        **options: Any,
    ) -> DataProductDependencyPage: ...
    def list_dependencies(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> DataProductDependencyPage: ...
    def get_direct_upstream(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> Sequence[Any]: ...
    def get_direct_downstream(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> Sequence[Any]: ...
    def get_transitive_upstream(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Any: ...
    def get_transitive_downstream(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Any: ...

    def create_slo(self, definition: DataProductSLODefinition) -> DataProductSLODefinition: ...
    def get_slo(
        self, tenant_id: str, environment: str, product_id: str, slo_id: str
    ) -> DataProductSLODefinition | None: ...
    def list_slos(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Sequence[Any]: ...
    def update_slo(self, definition: DataProductSLODefinition, *, expected_etag: str) -> DataProductSLODefinition: ...
    def activate_slo(self, tenant_id: str, environment: str, product_id: str, slo_id: str, **options: Any) -> Any: ...
    def disable_slo(self, tenant_id: str, environment: str, product_id: str, slo_id: str, **options: Any) -> Any: ...
    def archive_slo(self, tenant_id: str, environment: str, product_id: str, slo_id: str, **options: Any) -> Any: ...
    def append_slo_revision(self, definition: DataProductSLODefinition, **options: Any) -> None: ...
    def list_slo_revisions(
        self, tenant_id: str, environment: str, product_id: str, slo_id: str, **options: Any
    ) -> Sequence[Any]: ...
    def save_slo_evaluation(self, evaluation: DataProductSLOEvaluation) -> DataProductSLOEvaluation: ...
    def get_slo_evaluation(
        self, tenant_id: str, environment: str, product_id: str, slo_id: str, evaluation_id: str
    ) -> DataProductSLOEvaluation | None: ...
    def list_slo_evaluations(
        self, tenant_id: str, environment: str, product_id: str, slo_id: str, **options: Any
    ) -> Sequence[Any]: ...

    def save_reliability_event(
        self, tenant_id: str, environment: str, product_id: str, event: Any, **options: Any
    ) -> Any: ...
    def save_current_reliability(
        self, tenant_id: str, environment: str, product_id: str, value: Any, **options: Any
    ) -> Any: ...
    def get_current_reliability(self, tenant_id: str, environment: str, product_id: str) -> Any: ...
    def list_reliability_history(
        self, tenant_id: str, environment: str, product_id: str, **options: Any
    ) -> Sequence[Any]: ...
    def save_coverage(self, tenant_id: str, environment: str, product_id: str, value: Any, **options: Any) -> Any: ...
    def get_coverage(self, tenant_id: str, environment: str, product_id: str) -> Any: ...
    def save_impact(self, tenant_id: str, environment: str, product_id: str, value: Any, **options: Any) -> Any: ...
    def get_impact(self, tenant_id: str, environment: str, product_id: str) -> Any: ...
    def list_incidents(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Sequence[Any]: ...
    def list_changes(self, tenant_id: str, environment: str, product_id: str, **options: Any) -> Sequence[Any]: ...
    def readiness(self) -> dict[str, Any]: ...
