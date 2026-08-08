from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from .contracts import ActionDefinition, ActionPayload, Risk

CATALOGUE_NAME = "dataobs-safe-remediation"
CATALOGUE_VERSION = "1.0.0"


def _definition(action_type: str, name: str, target: str, strategy: str) -> ActionDefinition:
    return ActionDefinition(
        action_type=action_type,
        display_name=name,
        description=f"Run one bounded {name.lower()} through an internal DataObs service.",
        catalogue_version=CATALOGUE_VERSION,
        action_version="1.0.0",
        risk=Risk.LOW,
        target_type=target,
        payload_model=ActionPayload,
        required_permissions=("incidents:actions:execute",),
        required_incident_states=("open", "acknowledged", "investigating", "monitoring"),
        disallowed_incident_states=("resolved", "closed"),
        approval_required=False,
        timeout_seconds=300,
        max_attempts=2,
        executor_id=f"internal:{action_type}",
        verification_strategy=strategy,
        rollback_description="Cancel the pending task when supported; otherwise manual operator action is required.",
        feature_flag=f"incident_automation_{action_type}",
        runtime_requirements=("durable_internal_service_contract",),
        # No verified public contract exists at the audited baseline. Fail closed.
        execution_enabled=False,
    )


_DEFINITIONS = (
    _definition("rerun_scan", "Rerun scan", "scanner", "scan_task_v1"),
    _definition("freshness_recheck", "Freshness recheck", "monitor", "freshness_measurement_v1"),
    _definition("connection_test", "Connection test", "integration", "connection_test_v1"),
    ActionDefinition(
        action_type="suppress_notifications",
        display_name="Suppress notifications",
        description="Preview a bounded notification intent; execution is unavailable in v1.",
        catalogue_version=CATALOGUE_VERSION,
        action_version="1.0.0",
        risk=Risk.MEDIUM,
        target_type="incident",
        payload_model=ActionPayload,
        required_permissions=("incidents:actions:execute", "incidents:approvals:request"),
        required_incident_states=("open", "acknowledged", "investigating"),
        disallowed_incident_states=("resolved", "closed"),
        approval_required=True,
        timeout_seconds=60,
        max_attempts=1,
        executor_id="unconfigured:suppress_notifications",
        verification_strategy="notification_intent_v1",
        rollback_description="No mutation occurs in v1 because this action is preview-only.",
        feature_flag="incident_automation_suppress_notifications",
        runtime_requirements=("bounded_suppression_adapter", "critical_escalation_bypass"),
        execution_enabled=False,
    ),
)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class ActionCatalogue:
    def __init__(self, definitions: tuple[ActionDefinition, ...] = _DEFINITIONS) -> None:
        self._items = {item.action_type: item for item in definitions}
        if len(self._items) != len(definitions):
            raise ValueError("duplicate action type")
        serializable = []
        for item in definitions:
            data = asdict(item)
            data["payload_model"] = item.payload_model.__name__
            serializable.append(data)
        self.hash = canonical_hash(sorted(serializable, key=lambda item: item["action_type"]))

    def require(self, action_type: str) -> ActionDefinition:
        try:
            return self._items[action_type]
        except KeyError as exc:
            raise ValueError("action type is not allowlisted") from exc

    def list(self) -> tuple[ActionDefinition, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


CATALOGUE = ActionCatalogue()
