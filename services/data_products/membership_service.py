"""Event-audited Data Product membership application workflows."""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from typing import Literal, Sequence

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import (
    DataProductMembership,
    DataProductMembershipDecision,
    DataProductMembershipGenerationResult,
    DataProductMembershipProposal,
)
from services.data_products.events import ProductConsistencyError
from services.data_products.idempotency import hash_key, new_record, request_fingerprint, scoped_record_id
from services.data_products.membership_events import MembershipMutation
from services.data_products.reconciliation import (
    DataProductOperationService,
    RecoverableDataProductOperationCoordinator,
)
from services.data_products.repository import (
    DataProductMembershipExclusionResult,
    DataProductMembershipMutationResult,
    DataProductProposalDecisionResult,
    DataProductRepository,
    ProductVersionConflict,
)


class DataProductMembershipService:
    """Coordinates deterministic membership writes; repositories provide OCC."""

    def __init__(self, repository: DataProductRepository) -> None:
        self.repository = repository
        operation_service = DataProductOperationService(repository, worker_id="membership-runtime")
        self.coordinator = RecoverableDataProductOperationCoordinator(repository, operation_service)

    def _complete_runtime(self, tenant_id: str, environment: str, operation_id: str) -> None:
        outcome = self.coordinator.reconcile_pending(tenant_id, environment, operation_id)
        if outcome.status != "applied":
            raise ProductConsistencyError(outcome.error_code or f"operation_{outcome.status}")

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
    ) -> DataProductMembershipMutationResult:
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
        reservation = self.repository.reserve_idempotency(
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
        reserved = reservation.record
        if reserved.state == "completed":
            if not reserved.operation_id or reserved.result_revision is None or not reserved.result_etag:
                raise ProductConsistencyError("completed membership result reference is incomplete")
            replay = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
            if replay is None or replay.revision != reserved.result_revision or replay.etag != reserved.result_etag:
                raise ProductConsistencyError("immutable membership result is missing or divergent")
            terminal_id = mutation.event(outcome="applied", membership_id=membership_id).decision_id
            return DataProductMembershipMutationResult(
                membership=replay,
                operation_id=reserved.operation_id,
                replayed=True,
                decision_refs=(terminal_id,),
            )
        if reserved.state != "pending":
            raise ProductConsistencyError(f"idempotency reservation is {reserved.state}")
        existing = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
        if existing:
            if existing.state == "active":
                pending = mutation.event(outcome="pending", membership_id=membership_id)
                terminal = mutation.event(
                    outcome="applied",
                    membership_id=membership_id,
                    result_revision=existing.revision,
                    result_etag=existing.etag,
                )
                self.repository.append_membership_decision(tenant_id, environment, product_id, pending)
                self.repository.append_membership_decision(tenant_id, environment, product_id, terminal)
                self.repository.complete_idempotency(
                    record_id,
                    operation_id=mutation.operation_id,
                    revision=existing.revision,
                    etag=existing.etag,
                )
                return DataProductMembershipMutationResult(
                    membership=existing,
                    operation_id=mutation.operation_id,
                    decision_refs=(pending.decision_id, terminal.decision_id),
                )
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
        pending = mutation.event(outcome="pending", membership_id=membership_id)
        self.repository.append_membership_decision(tenant_id, environment, product_id, pending)
        self.coordinator.begin(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            operation_id=mutation.operation_id,
            operation_kind="manual_membership",
            idempotency_record_id=record_id,
            created_at=pending.occurred_at,
            payload={
                "request_fingerprint": mutation.fingerprint,
                "membership_id": membership_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "actor": actor,
                "reason": reason,
                "action": "membership_add",
                "expected_revision": None,
                "expected_etag": None,
                "pending_event_id": pending.decision_id,
                "membership_target": member.model_dump(mode="json"),
            },
        )
        created = self.repository.create_membership(tenant_id, environment, member)
        terminal = mutation.event(
            outcome="applied",
            membership_id=membership_id,
            result_revision=created.revision,
            result_etag=created.etag,
        )
        self.repository.append_membership_decision(
            tenant_id,
            environment,
            product_id,
            terminal,
        )
        # Generic result/history and the reservation are finalized together by
        # the shared recoverable coordinator; projection success is not itself
        # idempotency completion.
        self._complete_runtime(tenant_id, environment, mutation.operation_id)
        return DataProductMembershipMutationResult(
            membership=created,
            operation_id=mutation.operation_id,
            decision_refs=(pending.decision_id, terminal.decision_id),
        )

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

    @staticmethod
    def _proposal_identity(
        tenant_id: str, environment: str, product_id: str, entity_type: str, entity_id: str, source: str
    ) -> str:
        return sha256(
            "\0".join((tenant_id, environment, product_id, entity_type, entity_id, source)).encode()
        ).hexdigest()

    @staticmethod
    def _proposal_fingerprint(proposal: DataProductMembershipProposal) -> str:
        return request_fingerprint(
            tenant_id=proposal.tenant_id,
            environment=proposal.environment,
            product_id=proposal.product_id,
            action=f"proposal_evidence:{proposal.source}",
            body={
                "entity_type": proposal.entity_type,
                "entity_id": proposal.entity_id,
                "evidence_refs": sorted(set(proposal.evidence_refs)),
                "confidence": proposal.confidence,
                "source_coverage": proposal.source_coverage,
                "missing_inputs": sorted(set(proposal.missing_inputs)),
                "truncated": proposal.truncated,
            },
            actor="generator",
            reason="canonical proposal evidence",
            expected_etag=None,
        )

    def _generate_proposals(
        self,
        tenant_id: str,
        environment: str,
        product_id: str,
        *,
        source: Literal["lineage", "dependency"],
        evidence: Sequence[tuple[str, str, str]],
        max_proposals: int,
    ) -> DataProductMembershipGenerationResult:
        if self.repository.get_product(tenant_id, environment, product_id) is None:
            raise KeyError(product_id)
        grouped: dict[tuple[str, str], set[str]] = {}
        for entity_id, entity_type, reference in evidence:
            if not entity_id.strip() or not entity_type.strip() or not reference.strip():
                raise ValueError("proposal entity and evidence references must not be empty")
            grouped.setdefault((entity_id, entity_type), set()).add(reference)
        now = utc_now()
        generated = existing = superseded = 0
        candidates = sorted(grouped.items())
        for (entity_id, entity_type), references in candidates[:max_proposals]:
            proposal_id = self._proposal_identity(tenant_id, environment, product_id, entity_type, entity_id, source)
            latest = self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
            proposal = DataProductMembershipProposal(
                proposal_id=proposal_id,
                product_id=product_id,
                tenant_id=tenant_id,
                environment=environment,
                entity_id=entity_id,
                entity_type=entity_type,
                source=source,
                evidence_refs=sorted(references)[:50],
                confidence=1,
                source_coverage=1,
                truncated=len(references) > 50,
                observed_at=now,
                expires_at=now + timedelta(days=7),
                proposal_revision=(latest.proposal_revision + 1 if latest else 1),
            )
            if latest and self._proposal_fingerprint(latest) == self._proposal_fingerprint(proposal):
                existing += 1
                continue
            if latest and latest.state == "proposed":
                self.repository.supersede_membership_proposal(
                    tenant_id, environment, product_id, proposal_id, expected_revision=latest.proposal_revision
                )
                superseded += 1
            self.repository.create_membership_proposal(proposal)
            generated += 1
        return DataProductMembershipGenerationResult(
            generated=generated,
            existing=existing,
            superseded=superseded,
            truncated=len(candidates) > max_proposals,
            source_coverage=1 if evidence else 0,
            missing_inputs=[] if evidence else [source],
            observed_at=now,
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
        return self._generate_proposals(
            tenant_id, environment, product_id, source="lineage", evidence=evidence, max_proposals=max_proposals
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
        return self._generate_proposals(
            tenant_id, environment, product_id, source="dependency", evidence=evidence, max_proposals=max_proposals
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

    def get_proposal(self, tenant_id: str, environment: str, product_id: str, proposal_id: str):
        return self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)

    def _decide_proposal(
        self,
        action: Literal["accept", "reject", "expire", "supersede"],
        tenant_id: str,
        environment: str,
        product_id: str,
        proposal_id: str,
        *,
        actor: str,
        reason: str,
        idempotency_key: str,
        expected_revision: int,
    ) -> DataProductProposalDecisionResult:
        if not actor.strip() or not reason.strip() or not idempotency_key.strip() or expected_revision < 1:
            raise ValueError("actor, reason, idempotency key, and expected revision are required")
        mutation = MembershipMutation(
            tenant_id,
            environment,
            product_id,
            action,
            actor,
            reason,
            idempotency_key,
            {"proposal_id": proposal_id, "expected_revision": expected_revision},
            expected_revision=expected_revision,
        )
        record_id = scoped_record_id(tenant_id, environment, product_id, idempotency_key)
        reservation = self.repository.reserve_idempotency(
            record_id,
            new_record(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                action=f"proposal_{action}",
                key=idempotency_key,
                fingerprint=mutation.fingerprint,
            ),
        )
        reserved = reservation.record
        if reserved.state == "completed":
            proposal = self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
            if (
                not proposal
                or proposal.proposal_revision != expected_revision
                or proposal.state
                != (
                    {"accept": "accepted", "reject": "rejected", "expire": "expired", "supersede": "superseded"}[action]
                )
            ):
                raise ProductConsistencyError("proposal_result_inconsistent")
            membership = None
            if action == "accept":
                membership = self.repository.get_membership(
                    tenant_id,
                    environment,
                    product_id,
                    self._identity(product_id, proposal.entity_type, proposal.entity_id),
                )
                if membership is None or membership.proposal_id != proposal_id:
                    raise ProductConsistencyError("proposal_result_inconsistent")
                if membership.revision != reserved.result_revision or membership.etag != reserved.result_etag:
                    raise ProductConsistencyError("proposal_result_inconsistent")
            elif reserved.result_revision != expected_revision:
                raise ProductConsistencyError("proposal_result_inconsistent")
            terminal = mutation.event(
                outcome="applied",
                proposal_id=proposal_id,
                membership_id=membership.membership_id if membership else None,
            )
            return DataProductProposalDecisionResult(
                proposal, membership, reserved.operation_id or mutation.operation_id, True, (terminal.decision_id,)
            )
        proposal = self.repository.get_membership_proposal(tenant_id, environment, product_id, proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.proposal_revision != expected_revision:
            raise ProductVersionConflict("proposal_revision_conflict")
        if proposal.state != "proposed":
            raise ProductVersionConflict(f"proposal_already_{proposal.state}")
        membership = None
        membership_id = None
        pending = mutation.event(outcome="pending", proposal_id=proposal_id)
        self.repository.append_membership_decision(tenant_id, environment, product_id, pending)
        planned_at = utc_now()
        membership_id = (
            self._identity(product_id, proposal.entity_type, proposal.entity_id) if action == "accept" else None
        )
        membership_target = None
        if membership_id is not None:
            membership_target = {
                "membership_id": membership_id,
                "product_id": product_id,
                "tenant_id": tenant_id,
                "environment": environment,
                "entity_id": proposal.entity_id,
                "entity_type": proposal.entity_type,
                "source": "proposal",
                "proposal_id": proposal_id,
                "evidence_refs": tuple(proposal.evidence_refs),
                "confidence": proposal.confidence,
                "source_coverage": proposal.source_coverage,
                "observed_at": proposal.observed_at,
                "created_at": planned_at,
                "updated_at": planned_at,
                "created_by": actor,
                "revision": 1,
                "etag": sha256(f"{membership_id}:1".encode()).hexdigest(),
                "state": "active",
            }
        self.coordinator.begin(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            operation_id=mutation.operation_id,
            operation_kind=f"proposal_{action}",
            idempotency_record_id=record_id,
            created_at=pending.occurred_at,
            payload={
                "request_fingerprint": mutation.fingerprint,
                "actor": actor,
                "reason": reason,
                "action": action,
                "proposal_id": proposal_id,
                "proposal_revision": expected_revision,
                "expected_revision": expected_revision,
                "expected_source_state": "proposed",
                "target_proposal_state": {
                    "accept": "accepted",
                    "reject": "rejected",
                    "expire": "expired",
                    "supersede": "superseded",
                }[action],
                "membership_id": membership_id,
                "membership_target": membership_target,
                "pending_event_id": pending.decision_id,
            },
        )
        if action == "accept":
            membership = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
            if membership is None:
                membership = self.repository.create_membership(
                    tenant_id,
                    environment,
                    DataProductMembership(
                        membership_id=membership_id,
                        product_id=product_id,
                        tenant_id=tenant_id,
                        environment=environment,
                        entity_id=proposal.entity_id,
                        entity_type=proposal.entity_type,
                        source="proposal",
                        proposal_id=proposal_id,
                        evidence_refs=proposal.evidence_refs,
                        confidence=proposal.confidence,
                        source_coverage=proposal.source_coverage,
                        observed_at=proposal.observed_at,
                        created_at=planned_at,
                        updated_at=planned_at,
                        created_by=actor,
                        etag=sha256(f"{membership_id}:1".encode()).hexdigest(),
                    ),
                )
            elif membership.proposal_id != proposal_id or membership.state != "active":
                raise ProductVersionConflict("proposal_result_inconsistent")
        # Keep proposal transitions explicit and type-checkable; recovery must
        # never dispatch an arbitrary repository attribute from runtime data.
        handler = {
            "accept": self.repository.accept_membership_proposal,
            "reject": self.repository.reject_membership_proposal,
            "expire": self.repository.expire_membership_proposal,
            "supersede": self.repository.supersede_membership_proposal,
        }[action]
        decided = handler(tenant_id, environment, product_id, proposal_id, expected_revision=expected_revision)
        terminal = mutation.event(
            outcome="applied",
            proposal_id=proposal_id,
            membership_id=membership_id,
            result_revision=expected_revision,
            result_etag=decided.state,
        )
        self.repository.append_membership_decision(tenant_id, environment, product_id, terminal)
        self._complete_runtime(tenant_id, environment, mutation.operation_id)
        return DataProductProposalDecisionResult(
            decided, membership, mutation.operation_id, False, (pending.decision_id, terminal.decision_id)
        )

    def accept_proposal(self, *args, **kwargs):
        return self._decide_proposal("accept", *args, **kwargs)

    def reject_proposal(self, *args, **kwargs):
        return self._decide_proposal("reject", *args, **kwargs)

    def expire_proposal(self, *args, **kwargs):
        return self._decide_proposal("expire", *args, **kwargs)

    def supersede_proposal(self, *args, **kwargs):
        return self._decide_proposal("supersede", *args, **kwargs)

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
    ) -> DataProductMembershipExclusionResult:
        if not actor.strip() or not reason.strip() or not idempotency_key.strip() or not expected_etag.strip():
            raise ValueError("actor, reason, idempotency key, and If-Match are required")
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
        record_id = scoped_record_id(tenant_id, environment, product_id, idempotency_key)
        reservation = self.repository.reserve_idempotency(
            record_id,
            new_record(
                tenant_id=tenant_id,
                environment=environment,
                product_id=product_id,
                action="membership_exclude",
                key=idempotency_key,
                fingerprint=mutation.fingerprint,
            ),
        )
        reserved = reservation.record
        if reserved.state == "completed":
            member = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
            if (
                member is None
                or member.state != "excluded"
                or member.revision != reserved.result_revision
                or member.etag != reserved.result_etag
            ):
                raise ProductConsistencyError("immutable exclusion result is missing or divergent")
            terminal = mutation.event(
                outcome="applied", membership_id=membership_id, result_revision=member.revision, result_etag=member.etag
            )
            return DataProductMembershipExclusionResult(
                member, reserved.operation_id or mutation.operation_id, (terminal.decision_id,), True
            )
        pending = mutation.event(outcome="pending", membership_id=membership_id)
        self.repository.append_membership_decision(tenant_id, environment, product_id, pending)
        current = self.repository.get_membership(tenant_id, environment, product_id, membership_id)
        if current is None:
            raise KeyError(membership_id)
        target_revision = current.revision + 1
        target_etag = sha256(f"{current.etag}:excluded".encode()).hexdigest()
        self.coordinator.begin(
            tenant_id=tenant_id,
            environment=environment,
            product_id=product_id,
            operation_id=mutation.operation_id,
            operation_kind="membership_exclude",
            idempotency_record_id=record_id,
            created_at=pending.occurred_at,
            payload={
                "request_fingerprint": mutation.fingerprint,
                "actor": actor,
                "reason": reason,
                "action": "exclude",
                "membership_id": membership_id,
                "expected_revision": current.revision,
                "expected_etag": expected_etag,
                "target_state": "excluded",
                "target_revision": target_revision,
                "target_etag": target_etag,
                "pending_event_id": pending.decision_id,
            },
        )
        result = self.repository.exclude_membership(
            tenant_id, environment, product_id, membership_id, actor=actor, reason=reason, expected_etag=expected_etag
        )
        terminal = mutation.event(
            outcome="applied", membership_id=membership_id, result_revision=result.revision, result_etag=result.etag
        )
        self.repository.append_membership_decision(tenant_id, environment, product_id, terminal)
        self._complete_runtime(tenant_id, environment, mutation.operation_id)
        return DataProductMembershipExclusionResult(
            result, mutation.operation_id, (pending.decision_id, terminal.decision_id), False
        )

    def reconcile_membership_operation(self, tenant_id: str, environment: str, operation_id: str):
        from services.data_products.reconciliation import DataProductOperationService

        return DataProductOperationService(self.repository, worker_id="membership-reconciliation").reconcile_operation(
            tenant_id, environment, operation_id
        )
