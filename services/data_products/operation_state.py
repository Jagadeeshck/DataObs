"""Immutable operation history and OCC-controlled reconciliation state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any, Literal, Mapping

OperationOutcome = Literal["pending", "claimed", "checkpoint", "applied", "superseded", "failed"]


@dataclass(frozen=True)
class DataProductOperationHistoryEvent:
    event_id: str
    operation_id: str
    tenant_id: str
    environment: str
    product_id: str
    operation_kind: str
    action: str
    outcome: OperationOutcome
    actor: str
    reason: str
    request_fingerprint: str
    occurred_at: datetime
    expected_revision: int | None = None
    expected_etag: str | None = None
    result_revision: int | None = None
    result_etag: str | None = None
    plan_checksum: str | None = None
    result_checksum: str | None = None
    error_code: str | None = None
    worker_id: str | None = None
    applied_at: datetime | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class DataProductOperationCheckpoint:
    name: str
    checksum: str
    occurred_at: datetime


@dataclass(frozen=True)
class DataProductOperationClaim:
    operation_id: str
    owner: str
    generation: int
    claimed_at: datetime
    expires_at: datetime
    tenant_id: str = ""
    environment: str = ""
    product_id: str = ""


@dataclass(frozen=True)
class DataProductOperationFinalResult:
    revision: int
    etag: str
    checksum: str
    applied_at: datetime


@dataclass(frozen=True)
class DataProductOperationState:
    operation_id: str
    tenant_id: str
    environment: str
    product_id: str
    operation_kind: str
    status: Literal["pending", "claimed", "applied", "superseded", "failed"]
    attempt_count: int
    updated_at: datetime
    claim_owner: str | None = None
    claim_generation: int = 0
    claimed_at: datetime | None = None
    claim_expires_at: datetime | None = None
    last_checkpoint: DataProductOperationCheckpoint | None = None
    last_error_code: str | None = None
    plan_reference: str | None = None
    result_reference: str | None = None
    idempotency_record_id: str | None = None
    seq_no: int = 0
    primary_term: int = 1

    def claimed(self, claim: DataProductOperationClaim, *, now: datetime) -> "DataProductOperationState":
        return replace(
            self,
            status="claimed",
            attempt_count=self.attempt_count + 1,
            claim_owner=claim.owner,
            claim_generation=claim.generation,
            claimed_at=claim.claimed_at,
            claim_expires_at=claim.expires_at,
            updated_at=now,
            seq_no=self.seq_no + 1,
        )


class OperationClaimConflict(RuntimeError):
    """The caller does not own the current claim generation/CAS token."""


@dataclass(frozen=True)
class DataProductOperationPlan:
    """Immutable, checksum-addressed instructions used by a recovery handler."""

    reference: str
    tenant_id: str
    environment: str
    product_id: str
    operation_id: str
    operation_kind: str
    checksum: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class TypedDataProductOperationPlan:
    """Common immutable input for projection-aware mutation recovery."""

    tenant_id: str
    environment: str
    product_id: str
    operation_id: str
    operation_kind: str
    request_fingerprint: str
    idempotency_record_id: str
    actor: str
    reason: str
    expected_revision: int | None
    expected_etag: str | None
    target_checksum: str
    created_at: datetime

    def payload(self) -> Mapping[str, Any]:
        return asdict(self)


@dataclass(frozen=True, kw_only=True)
class ManualMembershipOperationPlan(TypedDataProductOperationPlan):
    membership_id: str
    entity_id: str
    entity_type: str
    pending_event_id: str


@dataclass(frozen=True, kw_only=True)
class ProposalDecisionOperationPlan(TypedDataProductOperationPlan):
    proposal_id: str
    proposal_action: Literal["accept", "reject", "expire", "supersede"]
    proposal_revision: int
    membership_id: str | None
    pending_event_id: str


@dataclass(frozen=True, kw_only=True)
class MembershipExclusionOperationPlan(TypedDataProductOperationPlan):
    membership_id: str
    pending_event_id: str


@dataclass(frozen=True, kw_only=True)
class DependencyReplacementOperationPlan(TypedDataProductOperationPlan):
    target_product_revision: int
    target_product_etag: str
    graph_version: str
    edge_checksums: tuple[str, ...]
    tombstone_checksums: tuple[str, ...]
    pending_event_id: str


@dataclass(frozen=True, kw_only=True)
class ProductLifecycleOperationPlan(TypedDataProductOperationPlan):
    source_lifecycle: str
    target_lifecycle: Literal["active", "deprecated", "archived"]
    target_revision: int
    target_etag: str
    pending_event_id: str


@dataclass(frozen=True)
class DataProductOperationResultEnvelope:
    """Immutable result persisted before the mutable state becomes terminal."""

    reference: str
    tenant_id: str
    environment: str
    product_id: str
    operation_id: str
    checksum: str
    payload: Mapping[str, Any]
    created_at: datetime


class OperationConsistencyError(RuntimeError):
    """A durable plan, projection, history event, or result has diverged."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
