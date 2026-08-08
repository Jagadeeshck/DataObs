from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from .catalogue import CATALOGUE, CATALOGUE_NAME, CATALOGUE_VERSION, canonical_hash
from .contracts import Execution, ExecutionState
from .repository import AutomationRepository


class VerificationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference: str = Field(min_length=1, max_length=200)
    target_id: str = Field(min_length=1, max_length=200)
    observed_at: datetime
    successful: bool
    recovery_observed: bool | None = None


def verify(repository: AutomationRepository, execution: Execution, evidence: VerificationEvidence) -> Execution:
    if execution.state != ExecutionState.VERIFICATION_PENDING:
        return execution
    if evidence.target_id != execution.target["id"] or evidence.observed_at < execution.created_at:
        execution.state, execution.error_code = ExecutionState.VERIFICATION_FAILED, "stale_or_wrong_target_evidence"
    elif evidence.successful:
        execution.state = ExecutionState.VERIFIED
    else:
        execution.state, execution.error_code = ExecutionState.VERIFICATION_FAILED, "operation_not_verified"
    execution.updated_at = datetime.now(timezone.utc)
    saved = repository.update_execution(execution, execution.lease_token)
    event_id = canonical_hash([execution.execution_id, "verification", evidence.reference])
    repository.append_event(
        "verification_event",
        event_id,
        {
            "@timestamp": execution.updated_at.isoformat(),
            "tenant_id": execution.tenant_id,
            "environment": execution.environment,
            "incident_id": execution.incident_id,
            "workflow_execution_id": execution.execution_id,
            "event_type": execution.state.value,
            "action_type": execution.action_type,
            "terminal_state": True,
            "request_id": execution.request_id,
            "correlation_id": execution.action_fingerprint,
            "metadata": {
                "verification_strategy": CATALOGUE.require(execution.action_type).verification_strategy,
                "evidence_reference": evidence.reference,
                "verified_execution": evidence.successful,
                "recovery_observed": evidence.recovery_observed,
                "catalogue_name": CATALOGUE_NAME,
                "catalogue_version": CATALOGUE_VERSION,
                "catalogue_hash": execution.catalogue_hash,
                "policy_hash": execution.policy_hash,
            },
        },
    )
    return saved
