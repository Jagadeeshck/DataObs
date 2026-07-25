from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDefinition:
    action_type: str
    adapter: str
    risk: str
    approval_required: bool
    verification_method: str


_ACTIONS = (
    ActionDefinition("rerun_scan", "dataobs", "low", False, "finding_recovered"),
    ActionDefinition("freshness_recheck", "dataobs", "low", False, "freshness_restored"),
    ActionDefinition("connection_test", "dataobs", "low", False, "source_healthy"),
    ActionDefinition("collect_evidence", "dataobs", "low", False, "evidence_collected"),
    ActionDefinition("verify_recovery", "dataobs", "low", False, "measured_telemetry"),
    ActionDefinition("rerun_airflow", "airflow", "medium", True, "rerun_succeeded"),
    ActionDefinition("rerun_dbt", "dbt", "medium", True, "rerun_succeeded"),
    ActionDefinition("rerun_spark", "spark", "medium", True, "rerun_succeeded"),
    ActionDefinition("restart_kafka_connect_task", "kafka_connect", "high", True, "connector_healthy"),
)


class ActionCatalogue:
    def __init__(self) -> None:
        self._actions = {item.action_type: item for item in _ACTIONS}

    def require(self, action_type: str) -> ActionDefinition:
        try:
            return self._actions[action_type]
        except KeyError as exc:
            raise ValueError("action type is not allowlisted") from exc

    def preview(self, action_type: str, *, target: str, current_state: str) -> dict[str, object]:
        action = self.require(action_type)
        return {
            "action_type": action.action_type,
            "target": target,
            "current_state": current_state,
            "proposed_operation": action.action_type,
            "expected_effect": action.verification_method,
            "risk": action.risk,
            "blast_radius": [target],
            "approval_required": action.approval_required,
            "timeout_seconds": 300,
            "verification_plan": action.verification_method,
            "rollback_guidance": "Stop and return the incident to investigating; no automatic rollback.",
        }
