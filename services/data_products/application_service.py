"""Authoritative event-first Data Product mutation workflow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from packages.domain_model.data_product import DataProduct
from services.data_products.repository import DataProductRepository
from services.data_products.service import DataProductService


@dataclass(frozen=True)
class MutationResult:
    product: DataProduct
    etag: str
    revision: int
    operation_id: str
    operation_state: str
    request_id: str
    trace_id: str


class DataProductApplicationService:
    """Adds transport metadata while delegating all mutation rules to one workflow."""

    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository
        self.lifecycle = DataProductService(repository)

    def _result(self, product: DataProduct, request_id: str, trace_id: str) -> MutationResult:
        # Operation identity is available from the persisted event. The scoped revision
        # lookup avoids exposing an Elasticsearch document identifier.
        operations = self.repository.list_pending_operations(
            product.tenant_id, product.environment, product_id=product.id, limit=1, include_applied=True
        )
        operation_id = operations[0].operation_id if operations else "reconciled"
        return MutationResult(product, product.etag, product.revision, operation_id, "applied", request_id, trace_id)

    def create(
        self,
        product: DataProduct,
        *,
        actor: str,
        reason: str,
        idempotency_key: str,
        request_id: str = "",
        trace_id: str = "",
    ) -> MutationResult:
        saved = self.lifecycle.create(product, actor=actor, reason=reason, idempotency_key=idempotency_key)
        return self._result(saved, request_id or str(uuid.uuid4()), trace_id or str(uuid.uuid4()))

    def update(
        self,
        product: DataProduct,
        *,
        if_match: str,
        actor: str,
        reason: str,
        idempotency_key: str,
        request_id: str = "",
        trace_id: str = "",
    ) -> MutationResult:
        saved = self.lifecycle.update(
            product, if_match=if_match, actor=actor, reason=reason, idempotency_key=idempotency_key
        )
        return self._result(saved, request_id or str(uuid.uuid4()), trace_id or str(uuid.uuid4()))

    def transition(
        self,
        action: str,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        if_match: str,
        actor: str,
        reason: str,
        idempotency_key: str,
        request_id: str = "",
        trace_id: str = "",
    ) -> MutationResult:
        if action not in {"activate", "deprecate", "archive"}:
            raise ValueError("unsupported lifecycle action")
        saved = getattr(self.lifecycle, action)(
            tenant_id,
            environment,
            product_id,
            if_match=if_match,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
        )
        return self._result(saved, request_id or str(uuid.uuid4()), trace_id or str(uuid.uuid4()))
