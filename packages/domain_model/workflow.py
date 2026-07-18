from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import ProductEntity
from .incident import deterministic_id


class WorkflowTriggerType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ALERT = "alert"
    TECHNICAL_PREVIEW_EVENT = "technical_preview_event"


class WorkflowExecutionStatus(StrEnum):
    PENDING = "pending"
    WAITING = "waiting"
    WAITING_FOR_INPUT = "waiting-for-input"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


TERMINAL_WORKFLOW_STATES = {
    WorkflowExecutionStatus.COMPLETED,
    WorkflowExecutionStatus.FAILED,
    WorkflowExecutionStatus.CANCELLED,
    WorkflowExecutionStatus.TIMED_OUT,
    WorkflowExecutionStatus.SKIPPED,
}


class ApprovalState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkflowDefinition(ProductEntity):
    workflow_id: str
    name: str
    kibana_space: str = "default"
    yaml_path: str
    yaml_checksum: str
    enabled: bool = False
    trigger_types: list[WorkflowTriggerType] = Field(default_factory=list)
    case_owner: str = "observability"


class WorkflowBinding(ProductEntity):
    binding_id: str = ""
    workflow_id: str
    rule_id: str
    kibana_space: str = "default"
    run_workflow_action_id: str | None = None
    enabled: bool = True

    def model_post_init(self, __context: Any) -> None:
        if not self.binding_id:
            self.binding_id = deterministic_id(
                "workflow-binding", [self.tenant_id, self.kibana_space, self.rule_id, self.workflow_id]
            )


class WorkflowStepExecution(ProductEntity):
    workflow_id: str
    execution_id: str
    step_id: str
    step_name: str
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    summary: str | None = None
    failure_details: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecution(ProductEntity):
    workflow_id: str
    trigger: WorkflowTriggerType
    workflow_status: WorkflowExecutionStatus = WorkflowExecutionStatus.RUNNING
    steps: list[WorkflowStepExecution | dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    incident_ref: str | None = None
    elastic_case_id: str | None = None
    executed_by: str | None = None
    test_execution: bool = False
    last_synchronized_at: datetime | None = None


class ApprovalRequest(ProductEntity):
    approval_id: str
    incident_id: str
    workflow_execution_id: str | None = None
    requested_action: str
    requester: str
    approver_scopes: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.LOW
    impact: str | None = None
    expires_at: datetime
    decision: ApprovalState = ApprovalState.REQUESTED
    comments: list[dict[str, Any]] = Field(default_factory=list)


class RemediationAction(ProductEntity):
    action_id: str
    incident_id: str
    action_type: str
    risk: ActionRisk
    preview: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    policy_decision: str = "allowed"
    approval_id: str | None = None
    timeout_seconds: int = 300
    verification: dict[str, Any] = Field(default_factory=dict)
    rollback_description: str


class VerificationResult(ProductEntity):
    action_id: str
    incident_id: str
    verified: bool
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    checked_at: datetime | None = None
