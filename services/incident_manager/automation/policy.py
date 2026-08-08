from __future__ import annotations

from dataclasses import dataclass

from .catalogue import canonical_hash
from .contracts import ActionDefinition, Risk

POLICY_VERSION = "1.0.0"
POLICY_HASH = canonical_hash({"version": POLICY_VERSION, "high_risk": "deny", "medium": "independent_approval"})


@dataclass(frozen=True)
class PolicyDecision:
    risk: Risk
    allowed: bool
    reason_code: str
    approval_required: bool


def evaluate(
    definition: ActionDefinition,
    *,
    environment: str,
    severity: str,
    incident_state: str,
    affected_asset_count: int,
    provider_ready: bool,
) -> PolicyDecision:
    risk = definition.risk
    if environment.lower() in {"prod", "production"} and (severity == "critical" or affected_asset_count > 25):
        risk = Risk.MEDIUM if risk in {Risk.READ_ONLY, Risk.LOW} else risk
    if severity == "critical" and definition.action_type == "suppress_notifications":
        return PolicyDecision(Risk.HIGH, False, "critical_suppression_denied", True)
    if risk in {Risk.HIGH, Risk.PROHIBITED}:
        return PolicyDecision(risk, False, "risk_not_permitted_v1", True)
    if incident_state in definition.disallowed_incident_states:
        return PolicyDecision(risk, False, "incident_state_disallowed", risk == Risk.MEDIUM)
    if definition.required_incident_states and incident_state not in definition.required_incident_states:
        return PolicyDecision(risk, False, "incident_state_not_allowed", risk == Risk.MEDIUM)
    if not provider_ready or not definition.execution_enabled:
        return PolicyDecision(
            risk, False, "executor_not_configured", definition.approval_required or risk == Risk.MEDIUM
        )
    return PolicyDecision(risk, True, "allowed", definition.approval_required or risk == Risk.MEDIUM)
