from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ApprovalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approver: str
    scopes: list[str]
    decision: ApprovalStatus
    comment: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    tenant_id: str
    environment: str
    action_id: str
    requester: str
    policy_version: str
    required_approvals: int = Field(default=1, ge=1, le=2)
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.REQUESTED
    decisions: list[ApprovalDecision] = Field(default_factory=list)


class ApprovalStore(Protocol):
    def get(self, tenant_id: str, approval_id: str) -> ApprovalRequest | None: ...
    def save(self, approval: ApprovalRequest) -> ApprovalRequest: ...


class ApprovalService:
    def __init__(self, repository: ApprovalStore) -> None:
        self.repository = repository

    def decide(
        self,
        tenant_id: str,
        approval_id: str,
        *,
        actor: str,
        scopes: list[str],
        decision: ApprovalStatus,
        comment: str,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        approval = self.repository.get(tenant_id, approval_id)
        if approval is None:
            raise KeyError(approval_id)
        checked_at = now or datetime.now(timezone.utc)
        if approval.status != ApprovalStatus.REQUESTED:
            raise ValueError("approval is no longer pending")
        if checked_at >= approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            self.repository.save(approval)
            raise ValueError("approval has expired")
        if actor == approval.requester:
            raise PermissionError("requester cannot approve their own action")
        if "approvals:decide" not in scopes:
            raise PermissionError("approvals:decide scope required")
        if any(item.approver == actor for item in approval.decisions):
            raise ValueError("approver has already decided")
        approval.decisions.append(ApprovalDecision(approver=actor, scopes=scopes, decision=decision, comment=comment))
        if decision == ApprovalStatus.REJECTED:
            approval.status = decision
        elif (
            decision == ApprovalStatus.APPROVED
            and len([item for item in approval.decisions if item.decision == ApprovalStatus.APPROVED])
            >= approval.required_approvals
        ):
            approval.status = ApprovalStatus.APPROVED
        return self.repository.save(approval)
