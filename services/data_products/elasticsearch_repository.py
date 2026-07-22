"""Production Data Product persistence with fixed resources and Elasticsearch OCC."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Sequence

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.data_product import (
    DataProduct,
    DataProductDependencyGraph,
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

PRODUCTS = "dataobs-data-products-v1"
REVISIONS = "dataobs-data-product-revisions-v1"
OPERATIONS = "dataobs-data-product-operation-state-v1"
IDEMPOTENCY = "dataobs-data-product-idempotency-v1"
MEMBERSHIPS = "dataobs-data-product-membership-v1"
PROPOSALS = "dataobs-data-product-membership-proposals-v1"
DECISIONS = "dataobs-data-product-membership-decisions-v1"
DEPENDENCIES = "dataobs-data-product-dependency-current-v1"
REQUIRED_RESOURCES = (
    PRODUCTS,
    REVISIONS,
    "dataobs-data-product-membership-v1",
    "dataobs-data-product-slos-v1",
    "dataobs-data-product-scorecards-v1",
    "dataobs-data-product-membership-proposals-v1",
    "dataobs-data-product-membership-decisions-v1",
    "dataobs-data-product-dependency-current-v1",
    "dataobs-data-product-slo-evaluations-v1",
    "dataobs-data-product-coverage-v1",
    "dataobs-data-product-impact-current-v1",
    "dataobs-data-product-operation-state-v1",
    "dataobs-data-product-idempotency-v1",
)


def scoped_id(tenant_id: str, environment: str, entity_id: str) -> str:
    if not tenant_id or not environment:
        raise ValueError("tenant_id and environment are mandatory")
    return sha256(f"{tenant_id}\0{environment}\0{entity_id}".encode()).hexdigest()


class ElasticsearchDataProductRepository:
    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    def reserve_idempotency(self, record_id: str, record: DataProductIdempotencyRecord) -> IdempotencyReservationResult:
        try:
            self.client.create(index=IDEMPOTENCY, id=record_id, document=record.model_dump(mode="json"))
            return IdempotencyReservationResult(status=IdempotencyReservationStatus.CREATED, record=record)
        except ConflictError as exc:
            existing = DataProductIdempotencyRecord.model_validate(
                self.client.get(index=IDEMPOTENCY, id=record_id)["_source"]
            )
            if existing.request_fingerprint != record.request_fingerprint:
                raise IdempotencyConflict("idempotency_conflict") from exc
            return IdempotencyReservationResult(
                status=IdempotencyReservationStatus(f"existing_{existing.state}"),
                record=existing,
                immutable_result_ref=existing.operation_id,
            )

    def get_idempotency(self, record_id: str) -> DataProductIdempotencyRecord | None:
        try:
            return DataProductIdempotencyRecord.model_validate(
                self.client.get(index=IDEMPOTENCY, id=record_id)["_source"]
            )
        except NotFoundError:
            return None

    def _transition_idempotency(self, record_id: str, **changes: Any) -> None:
        try:
            hit = self.client.get(index=IDEMPOTENCY, id=record_id, seq_no_primary_term=True)
        except NotFoundError as exc:
            raise ProductConsistencyError("idempotency reservation missing") from exc
        record = DataProductIdempotencyRecord.model_validate(hit["_source"])
        if record.state in {"completed", "failed", "superseded"}:
            if record.state == changes.get("state") and all(
                getattr(record, key) == value for key, value in changes.items()
            ):
                return
            raise ProductConsistencyError("terminal idempotency state cannot regress")
        changes["updated_at"] = datetime.now(timezone.utc)
        try:
            self.client.index(
                index=IDEMPOTENCY,
                id=record_id,
                document=record.model_copy(update=changes).model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise ProductVersionConflict("concurrent idempotency transition") from exc

    def complete_idempotency(self, record_id: str, *, operation_id: str, revision: int, etag: str) -> None:
        self._transition_idempotency(
            record_id,
            state="completed",
            operation_id=operation_id,
            result_revision=revision,
            result_etag=etag,
            completed_at=datetime.now(timezone.utc),
        )

    def fail_idempotency(self, record_id: str, *, error_code: str) -> None:
        self._transition_idempotency(record_id, state="failed", error_code=error_code)

    def supersede_idempotency(self, record_id: str, *, error_code: str = "newer_revision") -> None:
        self._transition_idempotency(record_id, state="superseded", error_code=error_code)

    def list_expired_idempotency(
        self, tenant_id: str, environment: str, *, now: datetime, limit: int = 100
    ) -> list[DataProductIdempotencyRecord]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        response = self.client.search(
            index=IDEMPOTENCY,
            size=limit,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"range": {"expires_at": {"lte": now.isoformat()}}},
                    ]
                }
            },
            sort=[{"expires_at": "asc"}, {"_id": "asc"}],
        )
        return [DataProductIdempotencyRecord.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    def create_product(self, product: DataProduct) -> DataProduct:
        try:
            self.client.create(
                index=PRODUCTS,
                id=scoped_id(product.tenant_id, product.environment, product.id),
                document=product.model_dump(mode="json"),
            )
        except ConflictError as exc:
            raise ProductVersionConflict("data product exists") from exc
        return product

    def get_product(self, tenant_id: str, environment: str, product_id: str) -> DataProduct | None:
        try:
            hit = self.client.get(
                index=PRODUCTS, id=scoped_id(tenant_id, environment, product_id), seq_no_primary_term=True
            )
        except NotFoundError:
            return None
        source = hit["_source"]
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            return None
        return DataProduct.model_validate(source)

    def get_products_by_ids(self, tenant_id: str, environment: str, product_ids: Sequence[str]) -> list[DataProduct]:
        ids = sorted(set(product_ids))
        if len(ids) > 10_000:
            raise ValueError("product_id_count_exceeded")
        if not ids:
            return []
        response = self.client.search(
            index=PRODUCTS,
            size=len(ids),
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"terms": {"id": ids}},
                    ]
                }
            },
            sort=[{"id": "asc"}, {"_id": "asc"}],
        )
        return [DataProduct.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    def list_products(
        self,
        tenant_id: str,
        environment: str,
        *,
        limit: int,
        search_after: Sequence[str | int | float] | None = None,
        **_: Any,
    ) -> list[DataProduct]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        body: dict[str, Any] = {
            "index": PRODUCTS,
            "size": limit,
            "query": {"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]}},
            "sort": [{"id": "asc"}, {"_id": "asc"}],
        }
        if search_after:
            body["search_after"] = list(search_after)
        hits = self.client.search(**body)["hits"]["hits"]
        return [DataProduct.model_validate(hit["_source"]) for hit in hits]

    def update_product(self, product: DataProduct, *, expected_etag: str) -> DataProduct:
        document_id = scoped_id(product.tenant_id, product.environment, product.id)
        try:
            hit = self.client.get(index=PRODUCTS, id=document_id, seq_no_primary_term=True)
            if hit["_source"].get("etag") != expected_etag:
                raise ProductVersionConflict("stale data product ETag")
            if int(hit["_source"].get("revision", 0)) >= product.revision:
                raise ProductVersionConflict("stale data product revision")
            self.client.index(
                index=PRODUCTS,
                id=document_id,
                document=product.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise ProductVersionConflict("concurrent data product update") from exc
        return product

    def append_revision(self, product: DataProduct, *, actor: str, reason: str) -> None:
        event_id = scoped_id(product.tenant_id, product.environment, f"{product.id}:{product.revision}")
        document = {
            "tenant_id": product.tenant_id,
            "environment": product.environment,
            "product_id": product.id,
            "revision": product.revision,
            "etag": product.etag,
            "actor": actor,
            "reason": reason,
            "document": product.model_dump(mode="json"),
        }
        try:
            self.client.create(index=REVISIONS, id=event_id, document=document)
        except ConflictError as exc:
            existing = self.client.get(index=REVISIONS, id=event_id)["_source"]
            if existing == document:
                return
            raise ProductConsistencyError("divergent same-revision payload") from exc

    def begin_operation(self, event: DataProductRevisionEvent, product: DataProduct) -> DataProductRevisionEvent:
        document = event.model_dump(mode="json") | {"document": product.model_dump(mode="json")}
        try:
            self.client.create(index=OPERATIONS, id=event.operation_id, document=document)
            return event
        except ConflictError as exc:
            existing = self.client.get(index=OPERATIONS, id=event.operation_id)["_source"]
            if existing.get("definition_checksum") != event.definition_checksum:
                raise ProductConsistencyError("divergent operation replay") from exc
            return DataProductRevisionEvent.model_validate(
                {key: value for key, value in existing.items() if key != "document"}
            )

    def finish_operation(self, event: DataProductRevisionEvent) -> None:
        try:
            pending = self.client.get(index=OPERATIONS, id=event.operation_id, seq_no_primary_term=True)
            source = pending["_source"]
            if source.get("definition_checksum") != event.definition_checksum:
                raise ProductConsistencyError("operation outcome has no matching pending operation")
            if source.get("outcome") != event.outcome:
                self.client.index(
                    index=OPERATIONS,
                    id=event.operation_id,
                    document=source | event.model_dump(mode="json"),
                    if_seq_no=pending["_seq_no"],
                    if_primary_term=pending["_primary_term"],
                )
        except (NotFoundError, ConflictError) as exc:
            raise ProductConsistencyError("operation outcome could not be committed") from exc
        outcome_id = scoped_id(event.tenant_id, event.environment, f"{event.operation_id}:{event.outcome}")
        try:
            self.client.create(index=REVISIONS, id=outcome_id, document=event.model_dump(mode="json"))
        except ConflictError as exc:
            existing = self.client.get(index=REVISIONS, id=outcome_id)["_source"]
            if existing != event.model_dump(mode="json"):
                raise ProductConsistencyError("divergent operation outcome") from exc

    def get_operation(self, tenant_id: str, environment: str, operation_id: str) -> DataProductRevisionEvent | None:
        try:
            source = self.client.get(index=OPERATIONS, id=operation_id)["_source"]
        except NotFoundError:
            return None
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            return None
        return DataProductRevisionEvent.model_validate({k: v for k, v in source.items() if k != "document"})

    def get_operation_result(
        self, tenant_id: str, environment: str, operation_id: str, expected_revision: int, expected_etag: str
    ) -> DataProductOperationResult:
        try:
            source = self.client.get(index=OPERATIONS, id=operation_id)["_source"]
        except NotFoundError as exc:
            raise ProductConsistencyError("immutable operation result missing") from exc
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            raise ProductConsistencyError("immutable operation result missing")
        if (
            source.get("outcome") != "applied"
            or source.get("revision") != expected_revision
            or source.get("etag") != expected_etag
        ):
            raise ProductConsistencyError("immutable operation result diverged")
        try:
            product = DataProduct.model_validate(source["document"])
        except (KeyError, ValueError) as exc:
            raise ProductConsistencyError("immutable operation snapshot missing") from exc
        return DataProductOperationResult(
            product=product,
            **{
                k: source[k]
                for k in (
                    "operation_id",
                    "action",
                    "outcome",
                    "revision",
                    "etag",
                    "definition_checksum",
                    "actor",
                    "reason",
                    "occurred_at",
                    "applied_at",
                )
            },
        )

    @staticmethod
    def _page_hits(response: dict[str, Any], model: Any, limit: int) -> tuple[list[Any], bool, list[Any] | None]:
        hits = response["hits"]["hits"]
        more = len(hits) > limit
        page = hits[:limit]
        return [model.model_validate(h["_source"]) for h in page], more, (page[-1].get("sort") if more else None)

    def _scoped_page(
        self,
        index: str,
        model: Any,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int,
        search_after: Sequence[str | int | float] | None = None,
        extra: list[dict[str, Any]] | None = None,
        sort: Sequence[dict[str, str]],
    ) -> tuple[list[Any], bool, list[Any] | None]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        filters = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"environment": environment}},
            {"term": {"product_id": product_id}},
        ] + (extra or [])
        request: dict[str, Any] = {
            "index": index,
            "size": limit + 1,
            "query": {"bool": {"filter": filters}},
            "sort": list(sort),
        }
        if search_after:
            request["search_after"] = list(search_after)
        return self._page_hits(self.client.search(**request), model, limit)

    def create_membership(
        self, tenant_id: str, environment: str, membership: DataProductMembership, *, create_only: bool = True
    ) -> DataProductMembership:
        if (membership.tenant_id, membership.environment) != (tenant_id, environment):
            raise ValueError("membership scope mismatch")
        document_id = scoped_id(tenant_id, environment, f"{membership.product_id}:{membership.membership_id}")
        try:
            self.client.create(index=MEMBERSHIPS, id=document_id, document=membership.model_dump(mode="json"))
        except ConflictError as exc:
            existing = DataProductMembership.model_validate(
                self.client.get(index=MEMBERSHIPS, id=document_id)["_source"]
            )
            if existing.model_dump(mode="json") == membership.model_dump(mode="json"):
                return existing
            raise ProductVersionConflict("divergent membership replay") from exc
        return membership

    def get_membership(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> DataProductMembership | None:
        try:
            source = self.client.get(
                index=MEMBERSHIPS, id=scoped_id(tenant_id, environment, f"{product_id}:{membership_id}")
            )["_source"]
        except NotFoundError:
            return None
        return (
            DataProductMembership.model_validate(source)
            if (source.get("tenant_id"), source.get("environment"), source.get("product_id"))
            == (tenant_id, environment, product_id)
            else None
        )

    def list_memberships(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ) -> DataProductMembershipPage:
        items, more, after = self._scoped_page(
            MEMBERSHIPS,
            DataProductMembership,
            tenant_id,
            environment,
            product_id,
            limit=limit,
            search_after=search_after,
            sort=({"updated_at": "desc"}, {"membership_id": "asc"}, {"_id": "asc"}),
        )
        return DataProductMembershipPage(items=items, has_more=more, search_after=after)

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
        document_id = scoped_id(tenant_id, environment, f"{product_id}:{membership_id}")
        hit = self.client.get(index=MEMBERSHIPS, id=document_id, seq_no_primary_term=True)
        current = DataProductMembership.model_validate(hit["_source"])
        if current.etag != expected_etag:
            raise ProductVersionConflict("stale membership ETag")
        now = datetime.now(timezone.utc)
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
        try:
            self.client.index(
                index=MEMBERSHIPS,
                id=document_id,
                document=updated.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise ProductVersionConflict("concurrent membership decision") from exc
        return updated

    def create_membership_proposal(self, proposal: DataProductMembershipProposal) -> DataProductMembershipProposal:
        document_id = scoped_id(
            proposal.tenant_id,
            proposal.environment,
            f"{proposal.product_id}:{proposal.proposal_id}:{proposal.proposal_revision}",
        )
        try:
            self.client.create(index=PROPOSALS, id=document_id, document=proposal.model_dump(mode="json"))
        except ConflictError as exc:
            existing = DataProductMembershipProposal.model_validate(
                self.client.get(index=PROPOSALS, id=document_id)["_source"]
            )
            if existing == proposal:
                return existing
            raise ProductVersionConflict("divergent proposal replay") from exc
        return proposal

    def get_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal | None:
        response = self.client.search(
            index=PROPOSALS,
            size=1,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                        {"term": {"proposal_id": proposal_id}},
                    ]
                }
            },
            sort=[{"proposal_revision": "desc"}, {"_id": "desc"}],
        )
        hits = response["hits"]["hits"]
        return DataProductMembershipProposal.model_validate(hits[0]["_source"]) if hits else None

    def list_membership_proposals(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ) -> DataProductMembershipProposalPage:
        items, more, after = self._scoped_page(
            PROPOSALS,
            DataProductMembershipProposal,
            tenant_id,
            environment,
            product_id,
            limit=limit,
            search_after=search_after,
            sort=(
                {"created_at": "desc"},
                {"proposal_revision": "desc"},
                {"proposal_id": "asc"},
                {"_id": "asc"},
            ),
        )
        return DataProductMembershipProposalPage(items=items, has_more=more, search_after=after)

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
        response = self.client.search(
            index=PROPOSALS,
            size=1,
            seq_no_primary_term=True,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                        {"term": {"proposal_id": proposal_id}},
                    ]
                }
            },
            sort=[{"proposal_revision": "desc"}, {"_id": "desc"}],
        )
        hits = response["hits"]["hits"]
        if not hits:
            raise KeyError(proposal_id)
        hit = hits[0]
        current = DataProductMembershipProposal.model_validate(hit["_source"])
        if expected_revision is not None and current.proposal_revision != expected_revision:
            raise ProductVersionConflict("proposal_revision_conflict")
        if current.state == state:
            return current
        if current.state != "proposed":
            raise ProductVersionConflict("proposal already has a terminal decision")
        updated = current.model_copy(update={"state": state})
        try:
            self.client.index(
                index=PROPOSALS,
                id=hit["_id"],
                document=updated.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise ProductVersionConflict("concurrent proposal decision") from exc
        return updated

    def accept_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options
    ) -> DataProductMembershipProposal:
        return self._transition_membership_proposal(
            tenant_id, environment, product_id, proposal_id, "accepted", **options
        )

    def reject_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options
    ) -> DataProductMembershipProposal:
        return self._transition_membership_proposal(
            tenant_id, environment, product_id, proposal_id, "rejected", **options
        )

    def expire_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options
    ) -> DataProductMembershipProposal:
        return self._transition_membership_proposal(
            tenant_id, environment, product_id, proposal_id, "expired", **options
        )

    def supersede_membership_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str, **options
    ) -> DataProductMembershipProposal:
        return self._transition_membership_proposal(
            tenant_id, environment, product_id, proposal_id, "superseded", **options
        )

    def append_membership_decision(
        self, tenant_id: str, environment: str, product_id: str, decision: DataProductMembershipDecision
    ) -> DataProductMembershipDecision:
        if (decision.tenant_id, decision.environment, decision.product_id) != (tenant_id, environment, product_id):
            raise ValueError("decision scope mismatch")
        document_id = scoped_id(tenant_id, environment, decision.decision_id)
        try:
            self.client.create(index=DECISIONS, id=document_id, document=decision.model_dump(mode="json"))
        except ConflictError as exc:
            existing = DataProductMembershipDecision.model_validate(
                self.client.get(index=DECISIONS, id=document_id)["_source"]
            )
            if existing == decision:
                return existing
            raise ProductConsistencyError("divergent decision replay") from exc
        return decision

    def list_membership_decisions(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ) -> DataProductMembershipDecisionPage:
        items, more, after = self._scoped_page(
            DECISIONS,
            DataProductMembershipDecision,
            tenant_id,
            environment,
            product_id,
            limit=limit,
            search_after=search_after,
            sort=({"decided_at": "desc"}, {"decision_id": "asc"}, {"_id": "asc"}),
        )
        return DataProductMembershipDecisionPage(items=items, has_more=more, search_after=after)

    def save_dependencies(
        self, tenant_id: str, environment: str, product_id: str, dependencies: Sequence[DataProductDependencyProjection]
    ) -> DataProductDependencyPage:
        current: list[DataProductDependencyProjection] = []
        after = None
        while True:
            page = self.list_dependencies(tenant_id, environment, product_id, limit=200, search_after=after)
            current.extend(page.items)
            if len(current) > 10_000:
                raise ValueError("dependency_count_exceeded")
            if not page.has_more:
                break
            if not page.search_after:
                raise ProductConsistencyError("dependency page missing continuation")
            after = page.search_after
        proposed = {edge.upstream_product_id: edge for edge in dependencies}
        now = datetime.now(timezone.utc)
        for edge in current:
            if not edge.removed and edge.upstream_product_id not in proposed:
                proposed[edge.upstream_product_id] = edge.model_copy(
                    update={
                        "removed": True,
                        "removed_at": now,
                        "removed_by_revision": max(
                            (item.product_revision for item in dependencies),
                            default=edge.product_revision + 1,
                        ),
                        "updated_at": now,
                    }
                )
        for edge in proposed.values():
            if (edge.tenant_id, edge.environment, edge.product_id) != (tenant_id, environment, product_id):
                raise ValueError("dependency scope mismatch")
            edge_id = scoped_id(tenant_id, environment, f"{product_id}:{edge.upstream_product_id}")
            document = edge.model_dump(mode="json")
            try:
                hit = self.client.get(index=DEPENDENCIES, id=edge_id, seq_no_primary_term=True)
            except NotFoundError:
                try:
                    self.client.create(index=DEPENDENCIES, id=edge_id, document=document)
                except ConflictError as exc:
                    raise ProductVersionConflict("concurrent dependency create") from exc
            else:
                existing = DataProductDependencyProjection.model_validate(hit["_source"])
                if existing == edge:
                    continue
                try:
                    self.client.index(
                        index=DEPENDENCIES,
                        id=edge_id,
                        document=document,
                        if_seq_no=hit["_seq_no"],
                        if_primary_term=hit["_primary_term"],
                    )
                except ConflictError as exc:
                    raise ProductVersionConflict("concurrent dependency update") from exc
        return DataProductDependencyPage(items=sorted(proposed.values(), key=lambda x: x.upstream_product_id))

    def list_dependencies(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ) -> DataProductDependencyPage:
        items, more, after = self._scoped_page(
            DEPENDENCIES,
            DataProductDependencyProjection,
            tenant_id,
            environment,
            product_id,
            limit=limit,
            search_after=search_after,
            sort=(
                {"removed": "asc"},
                {"upstream_product_id": "asc"},
                {"graph_version": "desc"},
                {"_id": "asc"},
            ),
        )
        return DataProductDependencyPage(items=items, has_more=more, search_after=after)

    def _dependency_graph(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        direction: str,
        *,
        max_depth: int = 8,
        max_nodes: int = 200,
    ) -> DataProductDependencyGraph:
        if not 1 <= max_depth <= 32 or not 1 <= max_nodes <= 1000:
            raise ValueError("dependency traversal bounds invalid")
        from services.data_products.dependencies import (
            DataProductDependencyTraversalBudget,
            traverse_frontiers,
        )

        edge_models: dict[tuple[str, str], DataProductDependencyProjection] = {}

        def load(frontier: Sequence[str], requested_direction: str):
            field = "product_id" if requested_direction == "upstream" else "upstream_product_id"
            after = None
            values: list[tuple[str, str]] = []
            while True:
                response = self.client.search(
                    index=DEPENDENCIES,
                    size=200,
                    query={
                        "bool": {
                            "filter": [
                                {"term": {"tenant_id": tenant_id}},
                                {"term": {"environment": environment}},
                                {"term": {"removed": False}},
                                {"terms": {field: list(frontier)}},
                            ]
                        }
                    },
                    sort=[{"product_id": "asc"}, {"upstream_product_id": "asc"}, {"_id": "asc"}],
                    search_after=after,
                )
                hits = response["hits"]["hits"]
                for hit in hits:
                    edge = DataProductDependencyProjection.model_validate(hit["_source"])
                    key = (edge.product_id, edge.upstream_product_id)
                    edge_models[key] = edge
                    values.append(key)
                if len(hits) < 200:
                    return values, True
                after = hits[-1].get("sort")
                if not after:
                    return values, False

        traversal = traverse_frontiers(
            product_id,
            direction,  # type: ignore[arg-type]
            DataProductDependencyTraversalBudget(max_depth=max_depth, max_nodes=max_nodes),
            load,  # type: ignore[arg-type]
        )
        edges = [edge_models[key] for key in traversal.edges]
        adjacency: dict[str, list[tuple[str, DataProductDependencyProjection]]] = {}
        for edge in edges:
            source, target = (
                (edge.product_id, edge.upstream_product_id)
                if direction == "upstream"
                else (edge.upstream_product_id, edge.product_id)
            )
            adjacency.setdefault(source, []).append((target, edge))
        queue = [(product_id, 0)]
        seen = {product_id}
        nodes: list[str] = []
        selected: list[DataProductDependencyProjection] = []
        cycle: list[str] = []
        truncated = False
        depth_reached = 0
        while queue:
            node, depth = queue.pop(0)
            depth_reached = max(depth_reached, depth)
            for target, edge in sorted(adjacency.get(node, []), key=lambda item: item[0]):
                if target in seen:
                    cycle = [node, target]
                    continue
                if depth >= max_depth or len(nodes) >= max_nodes:
                    truncated = True
                    continue
                seen.add(target)
                nodes.append(target)
                selected.append(edge)
                queue.append((target, depth + 1))
        versions = sorted({edge.graph_version for edge in selected})
        return DataProductDependencyGraph(
            nodes=nodes,
            edges=selected,
            direction=direction,
            depth_reached=depth_reached,
            visited_count=len(seen),
            truncated=truncated,
            cycle_detected=bool(cycle),
            cycle_path=cycle,
            graph_version=sha256("\0".join(versions).encode()).hexdigest(),
            observed_at=datetime.now(timezone.utc),
        )

    def get_direct_upstream(
        self, tenant_id: str, environment: str, product_id: str, *, max_nodes: int = 200
    ) -> DataProductDependencyGraph:
        return self._dependency_graph(tenant_id, environment, product_id, "upstream", max_depth=1, max_nodes=max_nodes)

    def get_direct_downstream(
        self, tenant_id: str, environment: str, product_id: str, *, max_nodes: int = 200
    ) -> DataProductDependencyGraph:
        return self._dependency_graph(
            tenant_id, environment, product_id, "downstream", max_depth=1, max_nodes=max_nodes
        )

    def get_transitive_upstream(
        self, tenant_id: str, environment: str, product_id: str, *, max_depth: int = 8, max_nodes: int = 200
    ) -> DataProductDependencyGraph:
        return self._dependency_graph(
            tenant_id, environment, product_id, "upstream", max_depth=max_depth, max_nodes=max_nodes
        )

    def get_transitive_downstream(
        self, tenant_id: str, environment: str, product_id: str, *, max_depth: int = 8, max_nodes: int = 200
    ) -> DataProductDependencyGraph:
        return self._dependency_graph(
            tenant_id, environment, product_id, "downstream", max_depth=max_depth, max_nodes=max_nodes
        )

    def get_product_revision(
        self, tenant_id: str, environment: str, product_id: str, revision: int
    ) -> DataProduct | None:
        response = self.client.search(
            index=OPERATIONS,
            size=1,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                        {"term": {"revision": revision}},
                    ]
                }
            },
            sort=[{"occurred_at": "desc"}, {"_id": "desc"}],
        )
        hits = response["hits"]["hits"]
        return DataProduct.model_validate(hits[0]["_source"]["document"]) if hits else None

    def list_pending_operations(
        self,
        tenant_id: str,
        environment: str,
        *,
        product_id: str | None = None,
        limit: int = 100,
        include_applied: bool = False,
    ) -> list[DataProductRevisionEvent]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        filters: list[dict[str, Any]] = [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]
        if product_id:
            filters.append({"term": {"product_id": product_id}})
        if not include_applied:
            filters.append({"term": {"outcome": "pending"}})
        response = self.client.search(
            index=OPERATIONS,
            size=limit,
            query={"bool": {"filter": filters}},
            sort=[{"occurred_at": "asc"}, {"_id": "asc"}],
        )
        return [
            DataProductRevisionEvent.model_validate({k: v for k, v in hit["_source"].items() if k != "document"})
            for hit in response["hits"]["hits"]
        ]

    def list_revisions(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 100,
        search_after: Sequence[str | int | float] | None = None,
    ) -> list[DataProductRevisionEvent]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        request: dict[str, Any] = {
            "index": REVISIONS,
            "size": limit + 1,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                    ]
                }
            },
            "sort": [
                {"revision": "desc"},
                {"occurred_at": "desc"},
                {"operation_id": "desc"},
                {"_id": "desc"},
            ],
        }
        if search_after:
            request["search_after"] = list(search_after)
        response = self.client.search(**request)
        return [
            DataProductRevisionEvent.model_validate({k: v for k, v in hit["_source"].items() if k != "document"})
            for hit in response["hits"]["hits"]
            if "operation_id" in hit["_source"]
        ]

    def readiness(self) -> dict[str, Any]:
        """Return diagnostic readiness; never collapse a partial migration to healthy."""
        resources: dict[str, dict[str, Any]] = {}
        reasons: list[dict[str, str]] = []
        for name in REQUIRED_RESOURCES:
            exists = bool(self.client.indices.exists(index=name))
            detail: dict[str, Any] = {"exists": exists, "alias_target_valid": False, "write_blocked": False}
            if not exists:
                reasons.append({"code": "resource_missing", "resource": name})
                resources[name] = detail
                continue
            aliases = self.client.indices.get_alias(index=name)
            concrete = next(iter(aliases))
            installed_aliases = aliases[concrete].get("aliases", {})
            write_alias = f"{name}-write"
            detail["alias_target_valid"] = bool(installed_aliases.get(write_alias, {}).get("is_write_index"))
            if not detail["alias_target_valid"]:
                reasons.append({"code": "write_alias_invalid", "resource": name})
            settings = self.client.indices.get_settings(index=name)[concrete].get("settings", {}).get("index", {})
            detail["write_blocked"] = str(settings.get("blocks", {}).get("write", "false")).lower() == "true"
            if detail["write_blocked"]:
                reasons.append({"code": "resource_write_blocked", "resource": name})
            mapping = self.client.indices.get_mapping(index=name)[concrete].get("mappings", {})
            detail["strict_mapping"] = mapping.get("dynamic") == "strict"
            if not detail["strict_mapping"]:
                reasons.append({"code": "strict_mapping_missing", "resource": name})
            resources[name] = detail
        return {"ready": not reasons, "resources": resources, "reasons": reasons}
