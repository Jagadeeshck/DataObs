from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProduct, DataProductRevisionEvent
from services.data_products.events import definition_checksum, operation_id
from services.data_products.idempotency import (
    IdempotencyPending,
    new_record,
    request_fingerprint,
    scoped_record_id,
)
from services.data_products.repository import DataProductRepository, ProductVersionConflict


def product_etag(product: DataProduct) -> str:
    return '"' + sha256(product.model_dump_json(exclude={"etag", "updated_at"}).encode()).hexdigest() + '"'


class DataProductService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def create(
        self,
        product: DataProduct,
        *,
        actor: str,
        reason: str = "created",
        idempotency_key: str | None = None,
    ) -> DataProduct:
        if not product.owner.team or not product.criticality:
            raise ValueError("owner and criticality are required")
        product.revision = 1
        self.validate_dependencies(product)
        product.etag = product_etag(product)
        event = self._pending(product, actor, reason, "create", idempotency_key)
        existing = self.repository.begin_operation(event, product)
        if existing.outcome == "applied":
            replay = self.repository.get_product(product.tenant_id, product.environment, product.id)
            if replay is None:
                raise RuntimeError("applied operation is missing current state")
            return replay
        created = self.repository.create_product(product)
        self.repository.finish_operation(event.model_copy(update={"outcome": "applied", "applied_at": utc_now()}))
        return created

    def get(self, tenant_id: str, environment: str, product_id: str) -> DataProduct:
        product = self.repository.get_product(tenant_id, environment, product_id)
        if product is None:
            raise KeyError(product_id)
        return product

    def list(self, tenant_id: str, environment: str, *, limit: int = 50, cursor: str | None = None):
        return self.repository.list_products(tenant_id, environment, limit=limit, cursor=cursor)

    def update(
        self,
        product: DataProduct,
        *,
        if_match: str | None,
        actor: str,
        reason: str = "updated",
        idempotency_key: str | None = None,
        action: str = "update",
    ) -> DataProduct:
        if not if_match:
            raise ProductVersionConflict("If-Match is required")
        current = self.repository.get_product(product.tenant_id, product.environment, product.id)
        if current is None:
            raise KeyError(product.id)
        if current.etag != if_match:
            raise ProductVersionConflict("stale data product ETag")
        product.revision = current.revision + 1
        self.validate_dependencies(product)
        product.updated_at = datetime.now(timezone.utc)
        product.etag = product_etag(product)
        event = self._pending(product, actor, reason, action, idempotency_key)
        existing = self.repository.begin_operation(event, product)
        if existing.outcome == "applied":
            replay = self.repository.get_product(product.tenant_id, product.environment, product.id)
            if replay and replay.revision >= product.revision:
                return replay
        saved = self.repository.update_product(product, expected_etag=if_match)
        self.repository.finish_operation(event.model_copy(update={"outcome": "applied", "applied_at": utc_now()}))
        return saved

    def _pending(
        self,
        product: DataProduct,
        actor: str,
        reason: str,
        action: str,
        idempotency_key: str | None,
    ) -> DataProductRevisionEvent:
        checksum = definition_checksum(product)
        key = idempotency_key or checksum
        return DataProductRevisionEvent(
            operation_id=operation_id(product.tenant_id, product.environment, product.id, product.revision, key),
            product_id=product.id,
            tenant_id=product.tenant_id,
            environment=product.environment,
            revision=product.revision,
            etag=product.etag,
            definition_checksum=checksum,
            actor=actor,
            reason=reason,
            action=action,
        )

    def _transition(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        target: str,
        *,
        if_match: str | None,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> DataProduct:
        if not idempotency_key:
            raise ValueError("Idempotency-Key is required")
        canonical_action = {"active": "activate", "deprecated": "deprecate", "archived": "archive"}[target]
        fingerprint = request_fingerprint(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            action=canonical_action,
            body={},
            actor=actor,
            reason=reason,
            expected_etag=if_match,
        )
        record_id = scoped_record_id(tenant_id, environment, product_id, idempotency_key)
        record = new_record(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            action=canonical_action,
            key=idempotency_key,
            fingerprint=fingerprint,
        )
        reserved = self.repository.reserve_idempotency(record_id, record)
        # Critically, replay is resolved before current lifecycle and ETag validation.
        if reserved.state == "completed":
            if reserved.result_revision is None:
                raise IdempotencyPending("completed result has no revision")
            replay = self.repository.get_product_revision(tenant_id, environment, product_id, reserved.result_revision)
            if replay is None or replay.etag != reserved.result_etag:
                raise IdempotencyPending("completed result is not yet visible")
            return replay
        if reserved.state == "pending" and reserved.operation_id:
            operation = self.repository.get_operation(tenant_id, environment, reserved.operation_id)
            if operation and operation.outcome == "applied":
                replay = self.repository.get_product_revision(tenant_id, environment, product_id, operation.revision)
                if replay is None or replay.etag != operation.etag:
                    raise IdempotencyPending("operation result is not yet visible")
                self.repository.complete_idempotency(
                    record_id, operation_id=operation.operation_id, revision=operation.revision, etag=operation.etag
                )
                return replay
        current = self.get(tenant_id, environment, product_id)
        allowed = {
            "draft": {"active", "archived"},
            "active": {"deprecated", "archived"},
            "deprecated": {"archived"},
            "archived": set(),
        }
        if target not in allowed[current.lifecycle_state]:
            raise ValueError(f"invalid lifecycle transition: {current.lifecycle_state} -> {target}")
        if target == "active" and (not current.owner.team or not current.criticality or not current.outputs):
            raise ValueError("activation requires owner, criticality, and at least one output")
        changed = current.model_copy(deep=True)
        changed.lifecycle_state = target
        saved = self.update(
            changed,
            if_match=if_match,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
            action=canonical_action,
        )
        operation = self._pending(
            saved,
            actor,
            reason,
            canonical_action,
            idempotency_key,
        )
        self.repository.complete_idempotency(
            record_id, operation_id=operation.operation_id, revision=saved.revision, etag=saved.etag
        )
        return saved

    def activate(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        if_match: str | None,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> DataProduct:
        return self._transition(
            tenant_id,
            environment,
            product_id,
            "active",
            if_match=if_match,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
        )

    def deprecate(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        if_match: str | None,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> DataProduct:
        return self._transition(
            tenant_id,
            environment,
            product_id,
            "deprecated",
            if_match=if_match,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
        )

    def archive(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        if_match: str | None,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> DataProduct:
        return self._transition(
            tenant_id,
            environment,
            product_id,
            "archived",
            if_match=if_match,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
        )

    def validate_dependencies(self, product: DataProduct, *, max_depth: int = 32, max_nodes: int = 1000) -> None:
        """Validate the complete scoped graph with deterministic, bounded traversal."""
        graph: dict[str, list[str]] = {product.id: sorted({d.upstream_product_id for d in product.dependencies})}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, depth: int) -> None:
            if depth > max_depth:
                raise ValueError("data product dependency depth limit exceeded")
            if node in visiting:
                raise ValueError("data product dependency cycle")
            if node in visited:
                return
            if len(visited) + len(visiting) >= max_nodes:
                raise ValueError("data product dependency node limit exceeded")
            visiting.add(node)
            if node not in graph:
                candidate = self.repository.get_product(product.tenant_id, product.environment, node)
                if candidate is None:
                    raise ValueError(f"unknown or cross-tenant dependency: {node}")
                graph[node] = sorted({d.upstream_product_id for d in candidate.dependencies})
            for nxt in graph[node]:
                visit(nxt, depth + 1)
            visiting.remove(node)
            visited.add(node)

        visit(product.id, 0)
