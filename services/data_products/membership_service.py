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
from services.data_products.idempotency import hash_key, new_record, request_fingerprint, scoped_record_id
from services.data_products.membership_events import MembershipMutation
from services.data_products.repository import DataProductRepository


class DataProductMembershipService:
    """Coordinates deterministic membership writes; repositories provide OCC."""

    def __init__(self, repository: DataProductRepository) -> None:
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
        if self.repository.get_product(tenant_id, environment, product_id) is None:
            raise KeyError(product_id)
        membership_id = self._identity(product_id, entity_type, entity_id)
        mutation = MembershipMutation(
            tenant_id,
            environment,
            product_id,
            "add",
            actor,
            reason,
            idempotency_key,
            {"entity_id": entity_id, "entity_type": entity_type},
        )
        record_id = scoped_record_id(tenant_id, environment, product_id, idempotency_key)
        self.repository.reserve_idempotency(
            record_id,
            new_record(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                action="membership_add",
                key=idempotency_key,
                fingerprint=mutation.fingerprint,
            ),
        )
        existing = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
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
        self.repository.append_membership_decision(
            tenant_id, environment, product_id, mutation.event(outcome="pending", membership_id=membership_id)
        )
        created = self.repository.create_membership(tenant_id, environment, member)
        self.repository.append_membership_decision(
            tenant_id,
            environment,
            product_id,
            mutation.event(
                outcome="applied",
                membership_id=membership_id,
                result_revision=created.revision,
                result_etag=created.etag,
            ),
        )
        self.repository.complete_idempotency(
            record_id, operation_id=mutation.operation_id, revision=created.revision, etag=created.etag
        )
        return created

    def get_membership(
        self, tenant_id: str, environment: str, product_id: str, membership_id: str
    ) -> DataProductMembership | None:
        return self.repository.get_membership(tenant_id, environment, product_id, membership_id)

    def list_members(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        limit: int = 50,
        search_after: Sequence[str | int | float] | None = None,
    ):
        return self.repository.list_memberships(
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
            if self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id):
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
            self.repository.create_membership_proposal(proposal)
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
        return self.repository.list_membership_proposals(
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
        return self.repository.list_membership_decisions(
            tenant_id, environment, product_id, limit=limit, search_after=search_after
        )

    def generate_dependency_proposals(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        evidence: Sequence[tuple[str, str, str]],
        max_proposals: int = 100,
    ):
        return self.generate_lineage_proposals(
            tenant_id, environment, product_id, evidence=evidence, max_proposals=max_proposals
        )

    def get_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal | None:
        return self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def accept_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal:
        return self.repository.accept_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def reject_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal:
        return self.repository.reject_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def expire_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal:
        return self.repository.expire_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def supersede_proposal(
        self, tenant_id: str, environment: str, product_id: str, proposal_id: str
    ) -> DataProductMembershipProposal:
        return self.repository.supersede_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def exclude_member(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        membership_id: str,
        *,
        actor: str,
        reason: str,
        idempotency_key: str,
        expected_etag: str,
    ) -> DataProductMembership:
        mutation = MembershipMutation(
            tenant_id,
            environment,
            product_id,
            "exclude",
            actor,
            reason,
            idempotency_key,
            {"membership_id": membership_id},
            expected_etag,
        )
        self.repository.append_membership_decision(
            tenant_id, environment, product_id, mutation.event(outcome="pending", membership_id=membership_id)
        )
        result = self.repository.exclude_membership(
            tenant_id, environment, product_id, membership_id, actor=actor, reason=reason, expected_etag=expected_etag
        )
        self.repository.append_membership_decision(
            tenant_id,
            environment,
            product_id,
            mutation.event(
                outcome="applied", membership_id=membership_id, result_revision=result.revision, result_etag=result.etag
            ),
        )
        return result

    def reconcile_membership_operation(self, tenant_id: str, environment: str, operation_id: str):
        from services.data_products.reconciliation import DataProductReconciler

        return DataProductReconciler(self.repository).reconcile_operation(tenant_id, environment, operation_id)
