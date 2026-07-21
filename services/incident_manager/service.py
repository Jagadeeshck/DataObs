from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from opentelemetry import metrics

from packages.domain_model.incident import Finding, Incident, IncidentState, deterministic_id
from packages.domain_model.workflow import ActionRisk, ApprovalState

from .correlator import correlation_key
from .deduplication import deduplication_key
from .lifecycle import transition
from .normalizer import normalize_event
from .repository import IncidentRepository, InMemoryIncidentRepository, VersionConflict
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
MAX_CONFLICT_ATTEMPTS = 3
logger = logging.getLogger(__name__)
_meter = metrics.get_meter("dataobs.incident_manager")
_counters = {
    name: _meter.create_counter(name)
    for name in (
        "incident_ingest_created_total",
        "incident_ingest_updated_total",
        "incident_ingest_exact_replay_total",
        "incident_ingest_stale_replay_total",
        "incident_ingest_conflict_total",
        "incident_ingest_retry_total",
        "incident_ingest_retry_exhausted_total",
    )
}


def incident_id(tenant_id: str, deduplication_key: str) -> str:
    """Return the stable v1 incident identifier used by pre-0012 workers."""
    return deterministic_id("incident", [tenant_id, deduplication_key])


@dataclass(frozen=True)
class FindingMergeDecision:
    incident: Incident
    changed: bool
    reason: str
    occurrence_added: bool


def decide_finding_merge(incident: Incident, finding: Finding) -> FindingMergeDecision:
    """Purely decide how a finding changes the incident projection.

    Older findings may safely enrich the monotonic asset set, but cannot replace
    evidence, timestamps, summaries, ownership, or severity inputs.
    """
    merged = deepcopy(incident)
    is_new = finding.id not in merged.finding_ids
    assets = sorted(set(merged.affected_assets + [finding.asset_id] + finding.downstream_impact))
    assets_changed = assets != merged.affected_assets
    is_newer = merged.last_observed_at is None or finding.last_observed_at > merged.last_observed_at
    same_observation = finding.last_observed_at == merged.last_observed_at
    evidence_enrichment = bool(finding.evidence) and not merged.most_recent_evidence

    if is_new:
        merged.finding_ids = sorted(set(merged.finding_ids + [finding.id]))
        merged.occurrence_count += 1
    merged.affected_assets = assets

    projection_changed = False
    if is_newer or evidence_enrichment:
        if is_newer:
            merged.last_observed_at = finding.last_observed_at
        # An older observation can only fill missing evidence, never replace it.
        if is_newer or not merged.most_recent_evidence:
            merged.most_recent_evidence = deepcopy(finding.evidence)
        if is_newer:
            merged.impact_summary = finding.summary
            merged.owner_team = finding.owner_team or merged.owner_team
            merged.business_service = finding.business_service or merged.business_service
        projection_changed = True
    elif same_observation and finding.evidence != merged.most_recent_evidence:
        # Equal-time corrections are deterministic: the canonical JSON maximum wins.
        current = str(sorted(merged.most_recent_evidence, key=str))
        incoming = str(sorted(finding.evidence, key=str))
        if incoming > current:
            merged.most_recent_evidence = deepcopy(finding.evidence)
            projection_changed = True

    if is_new or is_newer or projection_changed:
        severity, factors = calculate_severity(finding, recurrence=merged.occurrence_count)
        merged.severity, merged.severity_factors = severity, factors

    if is_new:
        return FindingMergeDecision(merged, True, "new_occurrence", True)
    if is_newer:
        return FindingMergeDecision(merged, True, "newer_replay", False)
    if assets_changed or projection_changed:
        return FindingMergeDecision(merged, True, "projection_enrichment", False)
    reason = (
        "stale_replay"
        if merged.last_observed_at and finding.last_observed_at < merged.last_observed_at
        else "exact_replay"
    )
    return FindingMergeDecision(incident, False, reason, False)


def merge_finding(incident: Incident, finding: Finding) -> Incident:
    """Compatibility wrapper for callers that only need the projected incident."""
    return decide_finding_merge(incident, finding).incident


class IncidentManagerService:
    def __init__(self, repo: IncidentRepository | None = None) -> None:
        # The in-memory implementation is deliberately opt-in outside tests. Production
        # composition must inject ElasticsearchIncidentRepository.
        self.repo = repo or InMemoryIncidentRepository()

    def ingest(self, event: dict[str, Any], *, tenant_id: str) -> dict[str, Any]:
        incoming = normalize_event(event, tenant_id=tenant_id)
        finding = self.repo.save_finding(incoming)
        dedup = deduplication_key(incoming)
        for attempt in range(MAX_CONFLICT_ATTEMPTS):
            incident = self.repo.find_incident_by_dedup(tenant_id, incoming.environment, dedup)
            try:
                if incident is not None:
                    decision = decide_finding_merge(incident, incoming)
                    if not decision.changed:
                        _counters[f"incident_ingest_{decision.reason}_total"].add(1)
                        logger.info("incident ingest replay", extra={"reason": decision.reason})
                        return self._result(finding, incident, decision)
                    incident = self.repo.update_incident(decision.incident)
                    _counters["incident_ingest_updated_total"].add(1)
                else:
                    sev, factors = calculate_severity(incoming)
                    incident = self.repo.create_incident(
                        Incident(
                            id=incident_id(tenant_id, dedup),
                            tenant_id=tenant_id,
                            environment=incoming.environment,
                            deduplication_key=dedup,
                            title=incoming.title,
                            correlation_key=correlation_key(incoming),
                            finding_ids=[incoming.id],
                            affected_assets=sorted(set([incoming.asset_id] + incoming.downstream_impact)),
                            severity=sev,
                            severity_factors=factors,
                            owner_team=incoming.owner_team,
                            business_service=incoming.business_service,
                            opened_at=datetime.now(timezone.utc),
                            first_observed_at=incoming.first_observed_at,
                            last_observed_at=incoming.last_observed_at,
                            impact_summary=incoming.summary,
                            most_recent_evidence=incoming.evidence,
                        )
                    )
                    decision = FindingMergeDecision(incident, True, "new_occurrence", True)
                    _counters["incident_ingest_created_total"].add(1)
                return self._result(finding, incident, decision)
            except VersionConflict:
                _counters["incident_ingest_conflict_total"].add(1)
                if attempt + 1 == MAX_CONFLICT_ATTEMPTS:
                    _counters["incident_ingest_retry_exhausted_total"].add(1)
                    raise
                _counters["incident_ingest_retry_total"].add(1)
        raise VersionConflict("incident version conflict")

    @staticmethod
    def _result(finding: Finding, incident: Incident, decision: FindingMergeDecision) -> dict[str, Any]:
        status = {
            "exact_replay": "replayed",
            "stale_replay": "stale",
            "new_occurrence": "created" if incident.occurrence_count == 1 else "updated",
        }.get(decision.reason, "updated")
        return {
            "finding": finding.model_dump(mode="json"),
            "incident": incident.model_dump(mode="json"),
            "ingestion": {
                "status": status,
                "reason": decision.reason,
                "occurrence_added": decision.occurrence_added,
                "incident_changed": decision.changed,
            },
        }

    def transition(
        self, tenant_id: str, incident_id: str, state: IncidentState, reason: str | None = None
    ) -> dict[str, Any]:
        incident = self.repo.get_incident(tenant_id, incident_id)
        if not incident:
            raise KeyError(incident_id)
        return self.repo.update_incident(transition(incident, state, reason=reason)).model_dump(mode="json")

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
