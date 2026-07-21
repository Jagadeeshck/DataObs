"""Event-audited Data Product membership application workflows."""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from typing import Sequence

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import (
    DataProductMembership,
    DataProductMembershipDecision,
    DataProductMembershipGenerationResult,
    DataProductMembershipProposal,
)
from services.data_products.idempotency import hash_key, request_fingerprint


class DataProductMembershipService:
    """Coordinates deterministic membership writes; repositories provide OCC."""

    def __init__(self, repository: object) -> None:
        self.repository = repository

    @staticmethod
    def _identity(product_id: str, entity_type: str, entity_id: str) -> str:
        return sha256(f"{product_id}\0{entity_type}\0{entity_id}".encode()).hexdigest()

    def add_manual_member(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        entity_id: str,
        entity_type: str,
        actor: str,
        reason: str,
        idempotency_key: str,
    ) -> DataProductMembership:
        if not all((actor.strip(), reason.strip(), idempotency_key.strip())):
            raise ValueError("actor, reason, and idempotency key are required")
        if getattr(self.repository, "get_product")(tenant_id, environment, product_id) is None:
            raise KeyError(product_id)
        membership_id = self._identity(product_id, entity_type, entity_id)
        existing = getattr(self.repository, "get_membership")(tenant_id, environment, product_id, membership_id)
        if existing:
            if existing.state == "active":
                return existing
            raise ValueError("excluded membership cannot be silently reactivated")
        now = utc_now()
        etag = sha256(f"{membership_id}:1".encode()).hexdigest()
        member = DataProductMembership(
            membership_id=membership_id,
            product_id=product_id,
            tenant_id=tenant_id,
            environment=environment,
            entity_id=entity_id,
            entity_type=entity_type,
            source="manual",
            observed_at=now,
            created_by=actor,
            etag=etag,
        )
        created = getattr(self.repository, "create_membership")(tenant_id, environment, member)
        decision = DataProductMembershipDecision(
            decision_id=sha256(f"manual:{membership_id}".encode()).hexdigest(),
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            membership_id=membership_id,
            decision="accept",
            actor=actor,
            reason=reason,
            idempotency_key_hash=hash_key(idempotency_key),
            request_fingerprint=request_fingerprint(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                action="manual_add",
                body={"membership": membership_id},
                actor=actor,
                reason=reason,
                expected_etag=None,
            ),
        )
        getattr(self.repository, "append_membership_decision")(tenant_id, environment, product_id, decision)
        return created

    def list_members(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ):
        return getattr(self.repository, "list_memberships")(
            tenant_id, environment, product_id, limit=limit, search_after=search_after
        )

    def generate_lineage_proposals(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        evidence: Sequence[tuple[str, str, str]],
        max_proposals: int = 100,
    ):
        now = utc_now()
        generated = existing = 0
        for entity_id, entity_type, evidence_ref in sorted(evidence)[:max_proposals]:
            proposal_id = self._identity(product_id, entity_type, entity_id)
            if getattr(self.repository, "get_membership_proposal")(tenant_id, environment, product_id, proposal_id):
                existing += 1
                continue
            proposal = DataProductMembershipProposal(
                proposal_id=proposal_id,
                product_id=product_id,
                tenant_id=tenant_id,
                environment=environment,
                entity_id=entity_id,
                entity_type=entity_type,
                source="lineage",
                evidence_refs=[evidence_ref],
                confidence=1,
                source_coverage=1,
                observed_at=now,
                expires_at=now + timedelta(days=7),
                proposal_revision=1,
            )
            getattr(self.repository, "create_membership_proposal")(proposal)
            generated += 1
        return DataProductMembershipGenerationResult(
            generated=generated,
            existing=existing,
            superseded=0,
            truncated=len(evidence) > max_proposals,
            source_coverage=1 if evidence else 0,
            missing_inputs=[] if evidence else ["lineage"],
            observed_at=now,
        )

    def list_proposals(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ):
        return getattr(self.repository, "list_membership_proposals")(
            tenant_id, environment, product_id, limit=limit, search_after=search_after
        )

    def list_decisions(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ):
        return getattr(self.repository, "list_membership_decisions")(
            tenant_id, environment, product_id, limit=limit, search_after=search_after
        )
