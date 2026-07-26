"""Production Data Product persistence with fixed resources and Elasticsearch OCC."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
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
from services.data_products.repository import DependencyEdgeSuperseded, ProductVersionConflict

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

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: ElasticsearchDataProductRepository._json_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [ElasticsearchDataProductRepository._json_value(item) for item in value]
        return value

        @staticmethod
        def _decision_document(decision: DataProductMembershipDecision) -> dict[str, Any]:
            document = decision.model_dump(mode="json")
            document["decision_reason"] = document.pop("reason")
            return document

        @staticmethod
        def _decision_from_source(source: dict[str, Any]) -> dict[str, Any]:
            restored = dict(source)
restored["reason"] = restored.pop(
                "decision_reason", restored.get("reason")
            )
            return restored

    @staticmethod
    def _state_document(state: DataProductOperationState) -> dict[str, Any]:
        document = ElasticsearchDataProductRepository._json_value(asdict(state))
        document.pop("seq_no", None)
        document.pop("primary_term", None)
        return {
            "operation_id": state.operation_id,
            "product_id": state.product_id,
            "tenant_id": state.tenant_id,
            "environment": state.environment,
            "action": state.operation_kind,
            "outcome": state.status,
            "occurred_at": state.updated_at.isoformat(),
            # `document` is flattened and therefore cannot provide date range
            # semantics.  Keep the compatibility copy in the envelope while
            # querying this strictly mapped value.
            "next_attempt_at": state.next_attempt_at.isoformat() if state.next_attempt_at else None,
            "document": document,
        }

    @staticmethod
    def _state_from_hit(hit: dict[str, Any]) -> DataProductOperationState:
        value = dict(hit["_source"]["document"])
        checkpoint = value.get("last_checkpoint")
        if checkpoint:
            checkpoint["occurred_at"] = datetime.fromisoformat(checkpoint["occurred_at"])
            value["last_checkpoint"] = DataProductOperationCheckpoint(**checkpoint)
        for key in ("updated_at", "claimed_at", "claim_expires_at", "next_attempt_at"):
            if value.get(key):
                value[key] = datetime.fromisoformat(value[key])
        value["seq_no"] = hit["_seq_no"]
        value["primary_term"] = hit["_primary_term"]
        return DataProductOperationState(**value)

    def create_operation_state(self, state: DataProductOperationState) -> None:
        if state.status != "pending" or not state.plan_reference:
            raise ValueError("operation state must begin pending with a plan reference")
        document_id = scoped_id(state.tenant_id, state.environment, f"state:{state.operation_id}")
        document = self._state_document(state)
        try:
            self.client.create(index=OPERATIONS, id=document_id, document=document)
        except ConflictError as exc:
            existing = self.client.get(index=OPERATIONS, id=document_id)["_source"]
            if existing != document:
                raise ProductConsistencyError("divergent operation state") from exc

    def get_operation_state(
        self, tenant_id: str, environment: str, operation_id: str
    ) -> DataProductOperationState | None:
        try:
            hit = self.client.get(
                index=OPERATIONS,
                id=scoped_id(tenant_id, environment, f"state:{operation_id}"),
                seq_no_primary_term=True,
            )
        except NotFoundError:
            return None
        if (hit["_source"].get("tenant_id"), hit["_source"].get("environment")) != (tenant_id, environment):
            return None
        return self._state_from_hit(hit)

    def list_reconcilable_operations(
        self,
        tenant_id: str,
        environment: str,
        *,
        limit: int = 100,
        operation_kind: str | None = None,
        now: datetime | None = None,
    ):
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        query_now = now or datetime.now(timezone.utc)
        if query_now.tzinfo is None or query_now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        query_instant = query_now.astimezone(timezone.utc).isoformat()
        filters: list[dict[str, Any]] = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"environment": environment}},
            {"terms": {"outcome": ["pending", "claimed"]}},
            {
                "bool": {
                    "should": [
                        {"term": {"outcome": "pending"}},
                        {"range": {"document.claim_expires_at": {"lte": query_instant}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            {"exists": {"field": "document.status"}},
            {
                "bool": {
                    "should": [
                        {"bool": {"must_not": {"exists": {"field": "next_attempt_at"}}}},
                        {"range": {"next_attempt_at": {"lte": query_instant}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
        ]
        if operation_kind is not None:
            # Filtering belongs in the query: applying it after `size` silently
            # starves a kind when an older kind fills the requested batch.
            filters.append({"term": {"action": operation_kind}})
        response = self.client.search(
            index=OPERATIONS,
            size=limit,
            seq_no_primary_term=True,
            query={"bool": {"filter": filters}},
            sort=[{"occurred_at": "asc"}, {"operation_id": "asc"}, {"_id": "asc"}],
        )
        return [
            self._state_from_hit(hit)
            for hit in response["hits"]["hits"]
            if "status" in hit["_source"].get("document", {})
        ]

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
        if state.status not in {"pending", "claimed"} or (
            state.status == "claimed" and state.claim_expires_at and state.claim_expires_at > now
        ):
            raise OperationClaimConflict("operation_claim_conflict")
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
        self._replace_state(state.claimed(claim, now=now), expected_seq_no, expected_primary_term)
        return claim

    def _replace_state(self, state, seq_no, primary_term):
        try:
            self.client.index(
                index=OPERATIONS,
                id=scoped_id(state.tenant_id, state.environment, f"state:{state.operation_id}"),
                document=self._state_document(state),
                if_seq_no=seq_no,
                if_primary_term=primary_term,
            )
        except ConflictError as exc:
            raise OperationClaimConflict("operation_claim_conflict") from exc

    def _owned_state(self, claim: DataProductOperationClaim):
        if not claim.tenant_id or not claim.environment or not claim.product_id:
            raise OperationClaimConflict("operation_claim_conflict")
        state = self.get_operation_state(claim.tenant_id, claim.environment, claim.operation_id)
        now = datetime.now(timezone.utc)
        if (
            state is None
            or state.product_id != claim.product_id
            or state.status != "claimed"
            or (
                state.claim_owner,
                state.claim_generation,
            )
            != (claim.owner, claim.generation)
            or state.claim_expires_at is None
            or state.claim_expires_at <= now
        ):
            raise OperationClaimConflict("operation_claim_conflict")
        return state

    def renew_operation_claim(self, claim, *, expires_at):
        state = self._owned_state(claim)
        self._replace_state(replace(state, claim_expires_at=expires_at), state.seq_no, state.primary_term)
        return replace(claim, expires_at=expires_at)

    def assert_operation_claim(self, claim):
        self._owned_state(claim)

    def checkpoint_operation(self, claim, checkpoint):
        state = self._owned_state(claim)
        self._replace_state(
            replace(state, last_checkpoint=checkpoint, updated_at=checkpoint.occurred_at),
            state.seq_no,
            state.primary_term,
        )

    def _finalize_operation(self, claim, status, *, result=None, error_code=None):
        state = self._owned_state(claim)
        updated = result.applied_at if result else datetime.now(timezone.utc)
        final = replace(
            state,
            status=status,
            claim_owner=None,
            claimed_at=None,
            claim_expires_at=None,
            result_reference=result.checksum if result else state.result_reference,
            last_error_code=error_code,
            updated_at=updated,
        )
        self._replace_state(final, state.seq_no, state.primary_term)

    def complete_operation(self, claim, result):
        self._finalize_operation(claim, "applied", result=result)

    def supersede_operation(self, claim, *, error_code):
        self._finalize_operation(claim, "superseded", error_code=error_code)

    def fail_operation(self, claim, *, error_code):
        self._finalize_operation(claim, "failed", error_code=error_code)

    def schedule_operation_retry(self, claim, *, error_code, next_attempt_at, retry_after_seconds):
        state = self._owned_state(claim)
        pending = replace(
            state,
            status="pending",
            claim_owner=None,
            claimed_at=None,
            claim_expires_at=None,
            last_retryable_error=error_code,
            last_error_code=error_code,
            next_attempt_at=next_attempt_at,
            retry_after_seconds=retry_after_seconds,
            updated_at=datetime.now(timezone.utc),
        )
        self._replace_state(pending, state.seq_no, state.primary_term)

    def release_operation_claim(self, claim):
        state = self._owned_state(claim)
        self._replace_state(
            replace(state, status="pending", claim_owner=None, claimed_at=None, claim_expires_at=None),
            state.seq_no,
            state.primary_term,
        )

    def append_operation_history(self, event: DataProductOperationHistoryEvent) -> None:
        event_id = scoped_id(
            event.tenant_id, event.environment, f"history:{event.product_id}:{event.operation_id}:{event.event_id}"
        )
        document = self._json_value(asdict(event))
        envelope = {
            "operation_id": event.operation_id,
            "product_id": event.product_id,
            "tenant_id": event.tenant_id,
            "environment": event.environment,
            "action": event.action,
            "outcome": event.outcome,
            "actor": event.actor,
            "reason": event.reason,
            "occurred_at": event.occurred_at.isoformat(),
            "error_code": event.error_code,
            "document": document,
        }
        try:
            self.client.create(index=OPERATIONS, id=event_id, document=envelope)
        except ConflictError as exc:
            if self.client.get(index=OPERATIONS, id=event_id)["_source"] != envelope:
                raise ProductConsistencyError("divergent immutable operation history") from exc

    def get_operation_history(self, tenant_id, environment, operation_id, *, limit=100):
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        response = self.client.search(
            index=OPERATIONS,
            size=limit,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"operation_id": operation_id}},
                        {"exists": {"field": "document.event_id"}},
                    ]
                }
            },
            sort=[{"occurred_at": "asc"}, {"_id": "asc"}],
        )
        events = []
        for hit in response["hits"]["hits"]:
            value = dict(hit["_source"].get("document", {}))
            if "event_id" not in value:
                continue
            for key in ("occurred_at", "applied_at"):
                if value.get(key):
                    value[key] = datetime.fromisoformat(value[key])
            events.append(DataProductOperationHistoryEvent(**value))
        return sorted(events, key=lambda event: (event.occurred_at, event.event_id))

    def _save_immutable_envelope(self, kind, reference, tenant_id, environment, product_id, operation_id, value):
        document_id = scoped_id(tenant_id, environment, f"{kind}:{product_id}:{operation_id}:{reference}")
        envelope = {
            "action": f"__{kind}",
            "tenant_id": tenant_id,
            "environment": environment,
            "product_id": product_id,
            "operation_id": operation_id,
            "document": self._json_value(asdict(value)),
        }
        try:
            self.client.create(index=OPERATIONS, id=document_id, document=envelope)
        except ConflictError as exc:
            if self.client.get(index=OPERATIONS, id=document_id)["_source"] != envelope:
                raise ProductConsistencyError(f"divergent {kind}") from exc

    def save_operation_plan(self, plan):
        canonical = sha256(
            json.dumps(plan.payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        if canonical != plan.checksum:
            raise ProductConsistencyError("operation plan checksum mismatch")
        self._save_immutable_envelope(
            "operation_plan", plan.reference, plan.tenant_id, plan.environment, plan.product_id, plan.operation_id, plan
        )

    def load_operation_plan(self, tenant_id, environment, product_id, operation_id):
        return self._load_immutable_envelope(
            "operation_plan", DataProductOperationPlan, tenant_id, environment, product_id, operation_id
        )

    def save_operation_result(self, result):
        canonical = sha256(
            json.dumps(result.payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        if canonical != result.checksum:
            raise ProductConsistencyError("operation result checksum mismatch")
        self._save_immutable_envelope(
            "operation_result",
            result.reference,
            result.tenant_id,
            result.environment,
            result.product_id,
            result.operation_id,
            result,
        )

    def load_operation_result(self, tenant_id, environment, product_id, operation_id):
        value = self._load_immutable_envelope(
            "operation_result", DataProductOperationResultEnvelope, tenant_id, environment, product_id, operation_id
        )
        if value and isinstance(value.created_at, str):
            value = replace(value, created_at=datetime.fromisoformat(value.created_at))
        return value

    def _load_immutable_envelope(self, kind, model, tenant_id, environment, product_id, operation_id):
        response = self.client.search(
            index=OPERATIONS,
            size=2,
            query={
                "bool": {
                    "filter": [
                        {"term": {"action": f"__{kind}"}},
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                        {"term": {"operation_id": operation_id}},
                    ]
                }
            },
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        if len(hits) != 1:
            raise ProductConsistencyError(f"ambiguous {kind}")
        return model(**hits[0]["_source"]["document"])

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

    def bind_or_verify_idempotency_operation(
        self,
        record_id: str,
        *,
        tenant_id: str,
        environment: str,
        product_id: str,
        action: str,
        request_fingerprint: str,
        expected_operation_id: str,
    ) -> DataProductIdempotencyRecord:
        """OCC-bind an operation id after verifying every request dimension."""
        try:
            hit = self.client.get(index=IDEMPOTENCY, id=record_id, seq_no_primary_term=True)
        except NotFoundError as exc:
            raise ProductConsistencyError("idempotency reservation missing") from exc
        record = DataProductIdempotencyRecord.model_validate(hit["_source"])
        binding = (
            record.tenant_id,
            record.environment,
            record.resource_id,
            record.action,
            record.request_fingerprint,
        )
        if binding != (tenant_id, environment, product_id, action, request_fingerprint) or record.operation_id not in (
            None,
            expected_operation_id,
        ):
            raise ProductConsistencyError("idempotency operation binding mismatch")
        if record.operation_id == expected_operation_id:
            return record
        bound = record.model_copy(update={"operation_id": expected_operation_id})
        try:
            self.client.index(
                index=IDEMPOTENCY,
                id=record_id,
                document=bound.model_dump(mode="json"),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
            return bound
        except ConflictError:
            # Identical concurrent bind is success after a realtime reread.
            current = self.get_idempotency(record_id)
            if (
                current is None
                or current.operation_id != expected_operation_id
                or (
                    current.tenant_id,
                    current.environment,
                    current.resource_id,
                    current.action,
                    current.request_fingerprint,
                )
                != binding
            ):
                raise ProductVersionConflict("concurrent idempotency binding")
            return current

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

    def repair_idempotency_terminal(
        self,
        record_id: str,
        expected_operation_id: str,
        expected_request_fingerprint: str,
        outcome: str,
        final_result_or_error: DataProductOperationFinalResult | str,
    ) -> None:
        """Repair an OCC-fenced reservation only after verifying its durable binding."""
        record = self.get_idempotency(record_id)
        if record is None:
            raise ProductConsistencyError("idempotency reservation missing operation")
        if record.request_fingerprint != expected_request_fingerprint or record.operation_id not in (
            None,
            expected_operation_id,
        ):
            raise ProductConsistencyError("idempotency operation binding mismatch")
        if outcome == "completed" and isinstance(final_result_or_error, DataProductOperationFinalResult):
            changes = {
                "state": "completed",
                "operation_id": expected_operation_id,
                "result_revision": final_result_or_error.revision,
                "result_etag": final_result_or_error.etag,
                "completed_at": final_result_or_error.applied_at,
            }
        elif outcome in {"failed", "superseded"} and isinstance(final_result_or_error, str):
            changes = {"state": outcome, "error_code": final_result_or_error}
        else:
            raise ValueError("unsupported idempotency terminal outcome")
        try:
            self._transition_idempotency(record_id, **changes)
        except ProductVersionConflict:
            current = self.get_idempotency(record_id)
            if not current or any(getattr(current, key) != value for key, value in changes.items()):
                raise

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

    def begin_dependency_operation(self, event, product, plan):
        plan_document = {
            "current_product_revision": plan.current_product_revision,
            "next_product_revision": plan.next_product_revision,
            "expected_product_etag": plan.expected_product_etag,
            "new_product_etag": plan.new_product_etag,
            "before_graph_version": plan.before_graph_version,
            "after_graph_version": plan.after_graph_version,
            "upserts": [edge.model_dump(mode="json") for edge in plan.upserts],
            "tombstones": [edge.model_dump(mode="json") for edge in plan.tombstones],
            "warnings": list(plan.warnings),
            "request_fingerprint": plan.request_fingerprint,
        }
        document = event.model_dump(mode="json") | {
            "document": {"product": product.model_dump(mode="json"), "dependency_plan": plan_document}
        }
        try:
            self.client.create(index=OPERATIONS, id=event.operation_id, document=document)
            return event
        except ConflictError as exc:
            existing = self.client.get(index=OPERATIONS, id=event.operation_id)["_source"]
            if existing != document:
                raise ProductConsistencyError("divergent dependency operation plan") from exc
            return event

    def load_dependency_operation_plan(self, tenant_id, environment, operation_id):
        from services.data_products.dependency_events import DataProductDependencyMutationPlan

        try:
            source = self.client.get(index=OPERATIONS, id=operation_id)["_source"]
            envelope = source["document"]
            raw = envelope["dependency_plan"]
        except (NotFoundError, KeyError):
            return None
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            return None
        plan = DataProductDependencyMutationPlan(
            current_product_revision=raw["current_product_revision"],
            next_product_revision=raw["next_product_revision"],
            expected_product_etag=raw["expected_product_etag"],
            new_product_etag=raw["new_product_etag"],
            before_graph_version=raw["before_graph_version"],
            after_graph_version=raw["after_graph_version"],
            upserts=tuple(DataProductDependencyProjection.model_validate(value) for value in raw["upserts"]),
            tombstones=tuple(DataProductDependencyProjection.model_validate(value) for value in raw["tombstones"]),
            warnings=tuple(raw["warnings"]),
            request_fingerprint=raw["request_fingerprint"],
        )
        event = DataProductRevisionEvent.model_validate(
            {key: value for key, value in source.items() if key != "document"}
        )
        return event, DataProduct.model_validate(envelope["product"]), plan

    def save_dependency_operation_result(self, result):
        from services.data_products.dependency_events import DependencyResultInconsistent

        try:
            hit = self.client.get(index=OPERATIONS, id=result.operation.operation_id, seq_no_primary_term=True)
        except NotFoundError as exc:
            raise DependencyResultInconsistent("dependency_result_inconsistent") from exc
        source = hit["_source"]
        payload = {
            "operation": result.operation.__dict__ | {"occurred_at": result.operation.occurred_at.isoformat()},
            "operation_result_product": result.operation_result_product.model_dump(mode="json"),
            "result_product_revision": result.result_product_revision,
            "result_product_etag": result.result_product_etag,
            "applied_at": result.applied_at.isoformat(),
            "result_definition_checksum": result.result_definition_checksum,
            "result_graph_version": result.result_graph_version,
            "active_dependencies": [edge.model_dump(mode="json") for edge in result.active_dependencies],
            "active_dependency_checksums": list(result.active_dependency_checksums),
            "removed_dependency_ids": list(result.removed_dependency_ids),
            "upserted_count": result.upserted_count,
            "removed_count": result.removed_count,
            "warnings": list(result.warnings),
            "request_fingerprint": result.request_fingerprint,
        }
        existing = source.get("document", {}).get("dependency_result")
        if existing is not None:
            if existing != payload:
                raise DependencyResultInconsistent("dependency_result_inconsistent")
            return
        envelope = source.get("document", {}) | {"dependency_result": payload}
        try:
            self.client.index(
                index=OPERATIONS,
                id=result.operation.operation_id,
                document=source | {"document": envelope},
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        except ConflictError as exc:
            raise DependencyResultInconsistent("dependency_result_inconsistent") from exc

    def get_dependency_operation_result(self, tenant_id, environment, product_id, operation_id):
        from services.data_products.dependency_events import (
            DataProductDependencyOperation,
            DataProductDependencyOperationResult,
            DependencyResultInconsistent,
        )

        try:
            source = self.client.get(index=OPERATIONS, id=operation_id)["_source"]
            raw = source["document"]["dependency_result"]
        except (NotFoundError, KeyError) as exc:
            raise DependencyResultInconsistent("dependency_result_inconsistent") from exc
        if (source.get("tenant_id"), source.get("environment"), source.get("product_id")) != (
            tenant_id,
            environment,
            product_id,
        ):
            raise DependencyResultInconsistent("dependency_result_inconsistent")
        return DataProductDependencyOperationResult(
            operation=DataProductDependencyOperation(
                **(raw["operation"] | {"occurred_at": datetime.fromisoformat(raw["operation"]["occurred_at"])})
            ),
            operation_result_product=DataProduct.model_validate(raw["operation_result_product"]),
            result_product_revision=raw["result_product_revision"],
            result_product_etag=raw["result_product_etag"],
            applied_at=datetime.fromisoformat(raw["applied_at"]),
            result_definition_checksum=raw["result_definition_checksum"],
            result_graph_version=raw["result_graph_version"],
            active_dependencies=tuple(
                DataProductDependencyProjection.model_validate(v) for v in raw["active_dependencies"]
            ),
            active_dependency_checksums=tuple(raw["active_dependency_checksums"]),
            removed_dependency_ids=tuple(raw["removed_dependency_ids"]),
            upserted_count=raw["upserted_count"],
            removed_count=raw["removed_count"],
            warnings=tuple(raw["warnings"]),
            request_fingerprint=raw["request_fingerprint"],
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
            document = ElasticsearchDataProductRepository._decision_document(decision)
            self.client.create(index=DECISIONS, id=document_id, document=document)
        except ConflictError as exc:
            existing_source = self.client.get(index=DECISIONS, id=document_id)["_source"]
            existing = DataProductMembershipDecision.model_validate(ElasticsearchDataProductRepository._decision_from_source(existing_source))
            if existing == decision:
                return existing
            raise ProductConsistencyError("divergent decision replay") from exc
        return decision

    def get_membership_decision(self, tenant_id, environment, product_id, decision_id):
        try:
            source = self.client.get(index=DECISIONS, id=scoped_id(tenant_id, environment, decision_id))["_source"]
        except NotFoundError:
            return None
        value = DataProductMembershipDecision.model_validate(ElasticsearchDataProductRepository._decision_from_source(source))
        if (value.tenant_id, value.environment, value.product_id) != (tenant_id, environment, product_id):
            return None
        return value

    def get_membership_decisions_for_operation(self, tenant_id, environment, product_id, operation_id):
        response = self.client.search(
            index=DECISIONS,
            size=200,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"product_id": product_id}},
                        {"term": {"operation_id": operation_id}},
                    ]
                }
            },
            sort=[{"occurred_at": "asc"}, {"decision_id": "asc"}, {"_id": "asc"}],
        )
        return tuple(
            DataProductMembershipDecision.model_validate(ElasticsearchDataProductRepository._decision_from_source(hit["_source"]))
            for hit in response["hits"]["hits"]
        )

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

    def read_complete_dependency_snapshot(self, tenant_id: str, environment: str, product_id: str, *, maximum: int):
        from services.data_products.dependency_events import DataProductDependencyReadSnapshot

        values: list[DataProductDependencyProjection] = []
        after = None
        while True:
            page = self.list_dependencies(
                tenant_id,
                environment,
                product_id,
                limit=min(200, maximum + 1),
                search_after=after,
            )
            values.extend(page.items)
            if len(values) > maximum:
                raise ValueError("dependency_snapshot_maximum_exceeded")
            if not page.has_more:
                break
            if not page.search_after:
                raise ProductConsistencyError("dependency page missing continuation")
            after = page.search_after
        ordered = tuple(sorted(values, key=lambda edge: (edge.removed, edge.upstream_product_id, edge.graph_version)))
        return DataProductDependencyReadSnapshot(ordered, len(ordered), True)

    def apply_dependency_mutation_plan(self, tenant_id, environment, product_id, plan):
        self.apply_dependency_upsert_chunk(tenant_id, environment, product_id, plan.upserts)
        self.apply_dependency_tombstone_chunk(tenant_id, environment, product_id, plan.tombstones)
        targets = (*plan.upserts, *plan.tombstones)
        return self.list_dependencies(tenant_id, environment, product_id, limit=max(1, min(200, len(targets))))

    def apply_dependency_upsert_chunk(self, tenant_id, environment, product_id, edges):
        self._apply_dependency_chunk(tenant_id, environment, product_id, edges, tombstone=False)

    def apply_dependency_tombstone_chunk(self, tenant_id, environment, product_id, edges):
        self._apply_dependency_chunk(tenant_id, environment, product_id, edges, tombstone=True)

    def _apply_dependency_chunk(self, tenant_id, environment, product_id, edges, *, tombstone):
        for edge in edges:
            if (edge.tenant_id, edge.environment, edge.product_id) != (tenant_id, environment, product_id):
                raise ProductConsistencyError("dependency_edge_scope_mismatch")
            if edge.removed is not tombstone:
                raise ProductConsistencyError("dependency_edge_removed_semantics_invalid")
            if tombstone and (edge.removed_at is None or edge.removed_by_revision != edge.product_revision):
                raise ProductConsistencyError("dependency_tombstone_metadata_invalid")
            if not edge.graph_version or edge.product_revision < 1:
                raise ProductConsistencyError("dependency_edge_version_invalid")
            edge_id = scoped_id(tenant_id, environment, f"{product_id}:{edge.upstream_product_id}")
            document = edge.model_dump(mode="json")
            try:
                hit = self.client.get(index=DEPENDENCIES, id=edge_id, seq_no_primary_term=True)
            except NotFoundError:
                try:
                    self.client.create(index=DEPENDENCIES, id=edge_id, document=document)
                except ConflictError as exc:
                    current = DataProductDependencyProjection.model_validate(
                        self.client.get(index=DEPENDENCIES, id=edge_id, realtime=True)["_source"]
                    )
                    self._classify_dependency_edge(current, edge, exc)
            else:
                current = DataProductDependencyProjection.model_validate(hit["_source"])
                if current == edge:
                    continue
                self._classify_dependency_edge(current, edge)
                try:
                    self.client.index(
                        index=DEPENDENCIES,
                        id=edge_id,
                        document=document,
                        if_seq_no=hit["_seq_no"],
                        if_primary_term=hit["_primary_term"],
                    )
                except ConflictError as exc:
                    latest = DataProductDependencyProjection.model_validate(
                        self.client.get(index=DEPENDENCIES, id=edge_id, realtime=True)["_source"]
                    )
                    self._classify_dependency_edge(latest, edge, exc)

    @staticmethod
    def _classify_dependency_edge(current, target, conflict=None):
        """Classify a realtime edge before/after OCC; only an older edge is writable."""
        if current == target:
            return
        if current.product_revision == target.product_revision:
            raise ProductConsistencyError("dependency_edge_same_revision_diverged") from conflict
        if current.product_revision > target.product_revision:
            raise DependencyEdgeSuperseded("dependency_edge_superseded") from conflict
        if conflict is not None:
            raise ProductVersionConflict("concurrent dependency update") from conflict

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
