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
    DataProductDependencyOperation,
    DataProductDependencyOperationResult,
    DependencyOperationPending,
    DependencyResultInconsistent,
    canonical_upstream_ids,
    dependency_request_fingerprint,
)
from services.data_products.events import definition_checksum
from services.data_products.idempotency import IdempotencyReservationStatus, new_record, scoped_record_id
from services.data_products.reconciliation import (
    DataProductOperationService,
    RecoverableDataProductOperationCoordinator,
)
from services.data_products.repository import DataProductRepository, ProductVersionConflict
from services.data_products.service import product_etag


class DataProductDependencyService:
    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository
        runtime = DataProductOperationService(repository, worker_id="dependency-runtime")
        self.coordinator = RecoverableDataProductOperationCoordinator(repository, runtime)

    def read_and_verify_complete_dependency_result(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        plan: DataProductDependencyMutationPlan,
    ) -> tuple[DataProductDependencyProjection, ...]:
        """Read the complete scope and verify every planned edge deterministically."""
        snapshot = self.repository.read_complete_dependency_snapshot(tenant_id, environment, product_id, maximum=10_000)
        if not snapshot.complete or snapshot.count != len(snapshot.dependencies):
            raise DependencyResultInconsistent("dependency_snapshot_incomplete")
        by_upstream: dict[str, DataProductDependencyProjection] = {}
        for edge in snapshot.dependencies:
            if edge.upstream_product_id in by_upstream:
                raise DependencyResultInconsistent("duplicate_upstream_dependency")
            by_upstream[edge.upstream_product_id] = edge
        for expected in (*plan.upserts, *plan.tombstones):
            actual = by_upstream.get(expected.upstream_product_id)
            if actual is None or self._edge_checksum(actual) != self._edge_checksum(expected):
                raise DependencyResultInconsistent("dependency_plan_edge_diverged")
        return tuple(
            sorted(
                (edge for edge in snapshot.dependencies if not edge.removed),
                key=lambda edge: edge.upstream_product_id,
            )
        )

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
            immutable = self.repository.get_dependency_operation_result(
                tenant_id, environment, product_id, record.operation_id
            )
            if (
                immutable.result_product_revision != record.result_revision
                or immutable.result_product_etag != record.result_etag
                or definition_checksum(immutable.operation_result_product) != immutable.result_definition_checksum
                or tuple(self._edge_checksum(edge) for edge in immutable.active_dependencies)
                != immutable.active_dependency_checksums
            ):
                raise DependencyResultInconsistent("dependency_result_inconsistent")
            return DataProductDependencyMutationResult(
                immutable.operation_result_product,
                immutable.active_dependencies,
                record.operation_id,
                True,
                immutable.warnings,
                immutable.removed_count,
                immutable.upserted_count,
                immutable.result_graph_version,
            )
        if reservation.status == IdempotencyReservationStatus.EXISTING_PENDING:
            operation_id = reservation.record.operation_id or sha256((record_id + fingerprint).encode()).hexdigest()
            outcome = self.coordinator.reconcile_pending(tenant_id, environment, operation_id)
            if outcome.status != "applied":
                raise DependencyOperationPending(operation_id)
            immutable = self.repository.get_dependency_operation_result(
                tenant_id, environment, product_id, operation_id
            )
            return DataProductDependencyMutationResult(
                immutable.operation_result_product,
                immutable.active_dependencies,
                operation_id,
                True,
                immutable.warnings,
                immutable.removed_count,
                immutable.upserted_count,
                immutable.result_graph_version,
                recovered=True,
            )

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
        self.repository.begin_dependency_operation(event, next_product, plan)  # durable plan before writes
        self.coordinator.begin(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            operation_id=operation_id,
            operation_kind="dependency_replace",
            idempotency_record_id=record_id,
            created_at=now,
            payload={
                "request_fingerprint": fingerprint,
                "actor": actor.strip(),
                "reason": reason.strip(),
                "action": "dependency_replace",
                "expected_revision": product.revision,
                "expected_etag": expected_etag,
                "target_product_revision": next_product.revision,
                "target_product_etag": next_product.etag,
                "graph_version": graph_version,
                "upstream_product_ids": canonical,
            },
        )
        self.repository.update_product(next_product, expected_etag=expected_etag)  # serialization token
        self.repository.apply_dependency_mutation_plan(tenant_id, environment, product_id, plan)
        self.repository.finish_operation(event.model_copy(update={"outcome": "applied", "applied_at": utc_now()}))
        active = self.read_and_verify_complete_dependency_result(tenant_id, environment, product_id, plan)
        applied_at = utc_now()
        operation = DataProductDependencyOperation(
            operation_id=operation_id,
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            actor=actor.strip(),
            reason=reason.strip(),
            request_fingerprint=fingerprint,
            idempotency_key_hash=sha256(idempotency_key.encode()).hexdigest(),
            expected_product_revision=product.revision,
            expected_product_etag=expected_etag,
            before_graph_version=plan.before_graph_version,
            after_graph_version=graph_version,
            before_checksum=self._snapshot_checksum(snapshot.dependencies),
            after_checksum=self._snapshot_checksum((*active, *tombstones)),
            outcome="applied",
            occurred_at=now,
        )
        self.repository.save_dependency_operation_result(
            DataProductDependencyOperationResult(
                operation=operation,
                operation_result_product=next_product.model_copy(deep=True),
                result_product_revision=next_product.revision,
                result_product_etag=next_product.etag,
                applied_at=applied_at,
                result_definition_checksum=definition_checksum(next_product),
                result_graph_version=graph_version,
                active_dependencies=active,
                active_dependency_checksums=tuple(self._edge_checksum(edge) for edge in active),
                removed_dependency_ids=tuple(edge.upstream_product_id for edge in tombstones),
                upserted_count=len(upserts),
                removed_count=len(tombstones),
                warnings=warnings,
                request_fingerprint=fingerprint,
            )
        )
        outcome = self.coordinator.reconcile_pending(tenant_id, environment, operation_id)
        if outcome.status != "applied":
            raise DependencyOperationPending(operation_id)
        return DataProductDependencyMutationResult(
            next_product,
            active,
            operation_id,
            False,
            warnings,
            len(tombstones),
            len(upserts),
            graph_version,
        )

    @staticmethod
    def _edge_checksum(edge: DataProductDependencyProjection) -> str:
        return sha256(edge.model_dump_json(exclude_none=False).encode()).hexdigest()

    @classmethod
    def _snapshot_checksum(cls, edges: Sequence[DataProductDependencyProjection]) -> str:
        return sha256(
            "\0".join(cls._edge_checksum(edge) for edge in sorted(edges, key=lambda e: e.upstream_product_id)).encode()
        ).hexdigest()

    def recover_dependency_operation(
        self, tenant_id: str, environment: str, product_id: str, operation_id: str, *, record_id: str
    ) -> DataProductDependencyMutationResult:
        loaded = self.repository.load_dependency_operation_plan(tenant_id, environment, operation_id)
        if loaded is None:
            raise DependencyOperationPending(operation_id)
        event, target_product, plan = loaded
        current = self.repository.get_product(tenant_id, environment, product_id)
        if current is None:
            raise DependencyOperationPending(operation_id)
        if current.etag == plan.expected_product_etag:
            self.repository.update_product(target_product, expected_etag=plan.expected_product_etag)
        elif current.etag != plan.new_product_etag or current.revision != plan.next_product_revision:
            self.repository.supersede_idempotency(record_id, error_code="product_advanced")
            raise DependencyResultInconsistent("dependency_result_inconsistent")
        page = self.repository.apply_dependency_mutation_plan(tenant_id, environment, product_id, plan)
        terminal = event.model_copy(update={"outcome": "applied", "applied_at": utc_now()})
        self.repository.finish_operation(terminal)
        active = tuple(
            sorted((edge for edge in page.items if not edge.removed), key=lambda edge: edge.upstream_product_id)
        )
        operation = DataProductDependencyOperation(
            operation_id=operation_id,
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            actor=event.actor,
            reason=event.reason,
            request_fingerprint=plan.request_fingerprint,
            idempotency_key_hash="redacted",
            expected_product_revision=plan.current_product_revision,
            expected_product_etag=plan.expected_product_etag,
            before_graph_version=plan.before_graph_version,
            after_graph_version=plan.after_graph_version,
            before_checksum="",
            after_checksum=self._snapshot_checksum(active),
            outcome="applied",
            occurred_at=event.occurred_at,
        )
        result = DataProductDependencyOperationResult(
            operation=operation,
            operation_result_product=target_product,
            result_product_revision=target_product.revision,
            result_product_etag=target_product.etag,
            applied_at=terminal.applied_at or utc_now(),
            result_definition_checksum=definition_checksum(target_product),
            result_graph_version=plan.after_graph_version,
            active_dependencies=active,
            active_dependency_checksums=tuple(self._edge_checksum(edge) for edge in active),
            removed_dependency_ids=tuple(edge.upstream_product_id for edge in plan.tombstones),
            upserted_count=len(plan.upserts),
            removed_count=len(plan.tombstones),
            warnings=plan.warnings,
            request_fingerprint=plan.request_fingerprint,
        )
        self.repository.save_dependency_operation_result(result)
        self.repository.complete_idempotency(
            record_id, operation_id=operation_id, revision=target_product.revision, etag=target_product.etag
        )
        return DataProductDependencyMutationResult(
            target_product,
            active,
            operation_id,
            False,
            plan.warnings,
            len(plan.tombstones),
            len(plan.upserts),
            plan.after_graph_version,
            recovered=True,
        )
