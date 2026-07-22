"""Durable, OCC-serialized declared-dependency replacement coordinator."""

from __future__ import annotations

from hashlib import sha256
from typing import Sequence

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import (
    DataProductDependency,
    DataProductDependencyProjection,
    DataProductRevisionEvent,
)
from services.data_products.dependencies import build_adjacency, find_cycle_path
from services.data_products.dependency_events import (
    DataProductDependencyMutationPlan,
    DataProductDependencyMutationResult,
    canonical_upstream_ids,
    dependency_request_fingerprint,
)
from services.data_products.events import definition_checksum
from services.data_products.idempotency import IdempotencyReservationStatus, new_record, scoped_record_id
from services.data_products.repository import DataProductRepository, ProductVersionConflict
from services.data_products.service import product_etag


class DataProductDependencyService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository

    def replace_declared_dependencies(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        upstream_ids: Sequence[str],
        *,
        expected_etag: str,
        actor: str,
        reason: str,
        idempotency_key: str,
    ) -> DataProductDependencyMutationResult:
        if not actor.strip() or not reason.strip() or not expected_etag.strip() or not idempotency_key.strip():
            raise ValueError("actor, reason, If-Match, and Idempotency-Key are required")
        canonical = canonical_upstream_ids(product_id, upstream_ids)
        fingerprint = dependency_request_fingerprint(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            upstream_product_ids=canonical,
            actor=actor,
            reason=reason,
            expected_product_etag=expected_etag,
        )
        record_id = scoped_record_id(tenant_id, environment, product_id, idempotency_key)
        reservation = self.repository.reserve_idempotency(
            record_id,
            new_record(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                action="dependency_replace",
                key=idempotency_key,
                fingerprint=fingerprint,
            ),
        )
        if reservation.status == IdempotencyReservationStatus.EXISTING_COMPLETED:
            record = reservation.record
            if not record.operation_id or not record.result_revision or not record.result_etag:
                raise RuntimeError("completed idempotency result is incomplete")
            immutable = self.repository.get_operation_result(
                tenant_id, environment, record.operation_id, record.result_revision, record.result_etag
            )
            snapshot = self.repository.read_complete_dependency_snapshot(
                tenant_id, environment, product_id, maximum=10_000
            )
            active = tuple(edge for edge in snapshot.dependencies if not edge.removed)
            return DataProductDependencyMutationResult(
                immutable.product,
                active,
                record.operation_id,
                True,
                (),
                0,
                0,
                active[0].graph_version if active else sha256(b"").hexdigest(),
            )
        if reservation.status == IdempotencyReservationStatus.EXISTING_PENDING:
            raise RuntimeError(f"dependency_operation_pending:{reservation.record.operation_id or record_id}")

        product = self.repository.get_product(tenant_id, environment, product_id)
        if product is None:
            self.repository.fail_idempotency(record_id, error_code="not_found")
            raise KeyError(product_id)
        if product.etag != expected_etag:
            self.repository.fail_idempotency(record_id, error_code="stale_etag")
            raise ProductVersionConflict("stale data product ETag")
        snapshot = self.repository.read_complete_dependency_snapshot(tenant_id, environment, product_id, maximum=10_000)
        upstream = {value.id: value for value in self.repository.get_products_by_ids(tenant_id, environment, canonical)}
        missing = sorted(set(canonical) - set(upstream))
        archived = sorted(key for key, value in upstream.items() if value.lifecycle_state == "archived")
        if missing or archived:
            self.repository.fail_idempotency(record_id, error_code="invalid_upstream")
            raise KeyError((missing + archived)[0])
        warnings = tuple(
            f"deprecated_upstream:{key}"
            for key, value in sorted(upstream.items())
            if value.lifecycle_state == "deprecated"
        )
        active_elsewhere = [
            (edge.product_id, edge.upstream_product_id)
            for edge in snapshot.dependencies
            if not edge.removed and edge.product_id != product_id
        ]
        cycle = find_cycle_path(build_adjacency(active_elsewhere + [(product_id, value) for value in canonical]))
        if cycle:
            self.repository.fail_idempotency(record_id, error_code="dependency_cycle")
            raise ValueError("dependency_cycle:" + " -> ".join(cycle))

        now = utc_now()
        graph_version = sha256("\0".join(canonical).encode()).hexdigest()
        next_product = product.model_copy(deep=True)
        next_product.dependencies = [
            DataProductDependency(upstream_product_id=value, observed_at=now) for value in canonical
        ]
        next_product.revision += 1
        next_product.updated_at = now
        next_product.etag = product_etag(next_product)
        current = {edge.upstream_product_id: edge for edge in snapshot.dependencies}
        upserts = tuple(
            DataProductDependencyProjection(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                upstream_product_id=value,
                product_revision=next_product.revision,
                graph_version=graph_version,
                observed_at=now,
                created_at=current[value].created_at if value in current else now,
                updated_at=now,
            )
            for value in canonical
        )
        tombstones = tuple(
            edge.model_copy(
                update={
                    "removed": True,
                    "removed_at": now,
                    "removed_by_revision": next_product.revision,
                    "updated_at": now,
                    "product_revision": next_product.revision,
                    "graph_version": graph_version,
                }
            )
            for key, edge in sorted(current.items())
            if not edge.removed and key not in canonical
        )
        plan = DataProductDependencyMutationPlan(
            product.revision,
            next_product.revision,
            expected_etag,
            next_product.etag,
            snapshot.dependencies[0].graph_version if snapshot.dependencies else "",
            graph_version,
            upserts,
            tombstones,
            warnings,
            fingerprint,
        )
        operation_id = sha256((record_id + fingerprint).encode()).hexdigest()
        event = DataProductRevisionEvent(
            operation_id=operation_id,
            product_id=product_id,
            tenant_id=tenant_id,
            environment=environment,
            revision=next_product.revision,
            etag=next_product.etag,
            definition_checksum=definition_checksum(next_product),
            actor=actor.strip(),
            reason=reason.strip(),
            action="update",
            occurred_at=now,
        )
        self.repository.begin_operation(event, next_product)  # durable repair anchor before writes
        self.repository.update_product(next_product, expected_etag=expected_etag)  # serialization token
        page = self.repository.apply_dependency_mutation_plan(tenant_id, environment, product_id, plan)
        self.repository.finish_operation(event.model_copy(update={"outcome": "applied", "applied_at": utc_now()}))
        self.repository.complete_idempotency(
            record_id, operation_id=operation_id, revision=next_product.revision, etag=next_product.etag
        )
        return DataProductDependencyMutationResult(
            next_product,
            tuple(edge for edge in page.items if not edge.removed),
            operation_id,
            False,
            warnings,
            len(tombstones),
            len(upserts),
            graph_version,
        )
