from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Incident, IncidentState, deterministic_id
from packages.domain_model.workflow import ActionRisk, ApprovalState

from .correlator import correlation_key
from .deduplication import deduplication_key
from .lifecycle import transition
from .normalizer import normalize_event
from .repository import IncidentRepository, InMemoryIncidentRepository
from .severity import calculate_severity

SAFE_ACTIONS = {
    "rerun_scan",
    "freshness_recheck",
    "connection_test",
    "acknowledge_incident",
    "assign_owner",
    "suppress_notifications",
    "add_case_comment",
    "resend_notification",
}


class IncidentManagerService:
    def __init__(self, repo: IncidentRepository | None = None) -> None:
        # The in-memory implementation is deliberately opt-in outside tests. Production
        # composition must inject ElasticsearchIncidentRepository.
        self.repo = repo or InMemoryIncidentRepository()

    def ingest(self, event: dict[str, Any], *, tenant_id: str) -> dict[str, Any]:
        finding = self.repo.save_finding(normalize_event(event, tenant_id=tenant_id))
        dedup = deduplication_key(finding)
        incident = self.repo.find_incident_by_dedup(tenant_id, dedup)
        if incident:
            incident.occurrence_count += 1
            incident.last_observed_at = finding.last_observed_at  # type: ignore[attr-defined]
            if finding.id not in incident.finding_ids:
                incident.finding_ids.append(finding.id)
            incident.affected_assets = sorted(
                set(incident.affected_assets + [finding.asset_id] + finding.downstream_impact)
            )
        else:
            sev, factors = calculate_severity(finding)
            incident = Incident(
                id=deterministic_id("incident", [tenant_id, dedup]),
                tenant_id=tenant_id,
                environment=finding.environment,
                deduplication_key=dedup,
                title=finding.title,
                correlation_key=correlation_key(finding),
                finding_ids=[finding.id],
                affected_assets=sorted(set([finding.asset_id] + finding.downstream_impact)),
                severity=sev,
                severity_factors=factors,
                owner_team=finding.owner_team,
                business_service=finding.business_service,
                opened_at=datetime.now(timezone.utc),
                impact_summary=finding.summary,
                most_recent_evidence=finding.evidence,
            )
        sev, factors = calculate_severity(finding, recurrence=incident.occurrence_count)
        incident.severity = sev
        incident.severity_factors = factors
        self.repo.save_incident(incident)
        return {"finding": finding.model_dump(mode="json"), "incident": incident.model_dump(mode="json")}

    def transition(
        self, tenant_id: str, incident_id: str, state: IncidentState, reason: str | None = None
    ) -> dict[str, Any]:
        incident = self.repo.get_incident(tenant_id, incident_id)
        if not incident:
            raise KeyError(incident_id)
        return self.repo.save_incident(transition(incident, state, reason=reason)).model_dump(mode="json")

    def preview_action(
        self, tenant_id: str, incident_id: str, action_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if action_type not in SAFE_ACTIONS:
            raise ValueError("unsafe or unsupported action")
        if not self.repo.get_incident(tenant_id, incident_id):
            raise KeyError(incident_id)
        return {
            "action_type": action_type,
            "risk": ActionRisk.LOW,
            "allowed": True,
            "changes": [],
            "payload_keys": sorted(payload),
        }

    def execute_action(
        self, tenant_id: str, incident_id: str, action_type: str, idempotency_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        key = f"{tenant_id}:{incident_id}:{idempotency_key}"
        if key in self.repo.actions:
            return self.repo.actions[key]
        self.preview_action(tenant_id, incident_id, action_type, payload)
        raise RuntimeError("action execution requires an allowlisted ActionExecutor adapter")

    def decide_approval(
        self, tenant_id: str, approval_id: str, decision: ApprovalState, comments: str | None = None
    ) -> dict[str, Any]:
        approval = self.repo.approvals.get(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        if approval.get("tenant_id") != tenant_id:
            raise KeyError(approval_id)
        approval.update(
            {"decision": decision.value, "comments": comments, "decided_at": datetime.now(timezone.utc).isoformat()}
        )
        self.repo.approvals[approval_id] = approval
        return approval
