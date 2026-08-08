from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Risk(StrEnum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class ApprovalState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    CONSUMED = "consumed"


class ExecutionState(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    ROLLBACK_RECOMMENDED = "rollback_recommended"


class ActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    target_id: str = Field(min_length=1, max_length=200)
    target_revision: str = Field(min_length=1, max_length=120)

    @field_validator("target_id", "target_revision")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        lowered = value.lower()
        if any(token in lowered for token in ("password", "secret", "token", "connection_string", "://")):
            raise ValueError("secret-like or URL values are not accepted")
        return value


@dataclass(frozen=True)
class ActionDefinition:
    action_type: str
    display_name: str
    description: str
    catalogue_version: str
    action_version: str
    risk: Risk
    target_type: str
    payload_model: type[ActionPayload]
    required_permissions: tuple[str, ...]
    required_incident_states: tuple[str, ...]
    disallowed_incident_states: tuple[str, ...]
    approval_required: bool
    timeout_seconds: int
    max_attempts: int
    executor_id: str
    verification_strategy: str
    rollback_description: str
    feature_flag: str
    runtime_requirements: tuple[str, ...]
    execution_enabled: bool


class Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    preview_id: str
    action_type: str
    action_version: str
    catalogue_name: str
    catalogue_version: str
    catalogue_hash: str
    policy_version: str
    policy_hash: str
    target: dict[str, str]
    risk: Risk
    allowed: bool
    policy_decision: str
    denial_reason: str | None
    approval_required: bool
    expected_changes: tuple[str, ...]
    expected_side_effects: tuple[str, ...]
    timeout_seconds: int
    retry_policy: dict[str, int]
    verification_plan: str
    rollback_description: str
    provider_state: str
    warnings: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    tenant_id: str
    environment: str
    incident_id: str
    incident_revision: str
    actor: str
    previewed_at: datetime
    expires_at: datetime
    payload_fingerprint: str
    action_fingerprint: str
    request_id: str


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str
    tenant_id: str
    environment: str
    incident_id: str
    incident_revision: str
    preview_id: str
    action_fingerprint: str
    action_type: str
    action_version: str
    catalogue_hash: str
    policy_hash: str
    risk: Risk
    target: dict[str, str]
    payload_fingerprint: str
    requester: str
    required_permission: str
    requested_at: datetime
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    impact: str = Field(min_length=1, max_length=1000)
    request_id: str
    state: ApprovalState = ApprovalState.REQUESTED
    revision: int = 0
    decided_by: str | None = None
    decision_comment: str | None = Field(default=None, max_length=1000)


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_id: str
    tenant_id: str
    environment: str
    incident_id: str
    incident_revision: str
    preview_id: str
    approval_id: str | None
    action_type: str
    action_fingerprint: str
    payload_fingerprint: str
    catalogue_hash: str
    policy_hash: str
    target: dict[str, str]
    actor: str
    request_id: str
    state: ExecutionState
    created_at: datetime
    updated_at: datetime
    timeout_seconds: int
    max_attempts: int
    attempt: int = 0
    lease_owner: str | None = None
    lease_token: int = 0
    lease_expires_at: datetime | None = None
    operation_reference: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    terminal: bool
    operation_reference: str
    retryable: bool = False
    safe_status: str = "accepted"


class ActionExecutor(Protocol):
    action_type: str
    cancellation_supported: bool

    def execute(self, execution: Execution) -> ExecutionResult: ...
    def lookup(self, execution: Execution) -> ExecutionResult: ...
    def cancel(self, execution: Execution) -> bool: ...
