"""Canonical immutable membership mutation events.

The coordinator intentionally does not claim atomicity across Elasticsearch indices:
pending evidence is durable before the OCC projection write and reconciliation closes
the operation after a process failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductMembershipDecision
from services.data_products.idempotency import hash_key, request_fingerprint


@dataclass(frozen=True)
class MembershipMutation:
    tenant_id: str
    environment: str
    product_id: str
    action: str
    actor: str
    reason: str
    idempotency_key: str
    body: dict[str, object]
    expected_etag: str | None = None
    expected_revision: int | None = None

    @property
    def fingerprint(self) -> str:
        return request_fingerprint(
            tenant_id=self.tenant_id,
            environment=self.environment,
            product_id=self.product_id,
            action=self.action,
            body=self.body,
            actor=self.actor,
            reason=self.reason,
            expected_etag=self.expected_etag
            or (str(self.expected_revision) if self.expected_revision is not None else None),
        )

    @property
    def operation_id(self) -> str:
        return sha256(
            f"{self.tenant_id}\0{self.environment}\0{self.product_id}\0{hash_key(self.idempotency_key)}".encode()
        ).hexdigest()

    def event(
        self,
        *,
        outcome: str,
        proposal_id: str | None = None,
        membership_id: str | None = None,
        result_revision: int | None = None,
        result_etag: str | None = None,
        error_code: str | None = None,
    ) -> DataProductMembershipDecision:
        now = utc_now()
        decision_id = sha256(f"{self.operation_id}:{outcome}".encode()).hexdigest()
        return DataProductMembershipDecision(
            decision_id=decision_id,
            operation_id=self.operation_id,
            tenant_id=self.tenant_id,
            environment=self.environment,
            product_id=self.product_id,
            proposal_id=proposal_id,
            membership_id=membership_id,
            decision=self.action,
            outcome=outcome,
            actor=self.actor,
            reason=self.reason,
            request_fingerprint=self.fingerprint,
            idempotency_key_hash=hash_key(self.idempotency_key),
            expected_revision=self.expected_revision,
            result_revision=result_revision,
            result_etag=result_etag,
            error_code=error_code,
            occurred_at=now,
            decided_at=now,
            applied_at=now if outcome != "pending" else None,
        )
