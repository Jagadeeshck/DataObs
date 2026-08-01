from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Incident, deterministic_id
from services.incident_manager.flood_control.contracts import FloodEvent, FloodWindow
from services.incident_manager.flood_control.evaluator import evaluate_flood
from services.incident_manager.flood_control.policy import V1_FLOOD_POLICY
from services.incident_manager.flood_control.repository import FloodRepository, NotificationDecision, StoredFlood

from .contracts import CorrelationDecision, CorrelationGroup
from .policy import V1_POLICY
from .repository import CorrelationRepository, DeferredEvaluation, StoredGroup
from .service import CorrelationService

MAX_OCC_RETRIES = 3
_SEVERITY = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class IncidentCorrelationCoordinator:
    """Durable, idempotent post-incident orchestration boundary."""

    def __init__(
        self, incident_repo: Any, correlation_repo: CorrelationRepository, flood_repo: FloodRepository
    ) -> None:
        self.incidents, self.correlations, self.floods = incident_repo, correlation_repo, flood_repo
        self.engine = CorrelationService(V1_POLICY)

    def process(self, incident: Incident) -> dict[str, Any]:
        revision = str(
            incident.seq_no if incident.seq_no is not None else incident.updated_at or incident.last_observed_at
        )
        existing = self.correlations.find_group_for_incident(incident.tenant_id, incident.environment, incident.id)
        candidates = self.correlations.find_candidate_groups(incident.tenant_id, incident.environment, incident)
        candidates = [c for c in candidates if not existing or c.group.id != existing.group.id]
        selected, decision = existing, None
        if not selected:
            for rank, candidate in enumerate(candidates, 1):
                representative = self.incidents.get_incident(
                    incident.tenant_id, candidate.group.representative_incident_id, incident.environment
                )
                if not representative:
                    continue
                evaluated = self.engine.evaluate(
                    incident,
                    representative,
                    revision=revision,
                    candidate_revision=str(representative.seq_no or 0),
                    existing_group_id=candidate.group.id,
                )
                if evaluated.action == "attach":
                    decision, selected = evaluated, candidate
                    break
        if selected is None:
            group_id = deterministic_id(
                "correlation-group",
                [
                    incident.tenant_id,
                    incident.environment,
                    incident.id,
                    V1_POLICY.name,
                    V1_POLICY.version,
                    V1_POLICY.canonical_hash,
                ],
            )
            decision_id = deterministic_id(
                "correlation-decision",
                [
                    incident.tenant_id,
                    incident.environment,
                    incident.id,
                    revision,
                    group_id,
                    V1_POLICY.name,
                    V1_POLICY.version,
                    V1_POLICY.canonical_hash,
                ],
            )
            decision = CorrelationDecision(
                decision_id,
                "create",
                incident.id,
                group_id,
                V1_POLICY.name,
                V1_POLICY.version,
                V1_POLICY.canonical_hash,
                datetime.now(timezone.utc),
                1.0,
                1.0,
                (),
                ("initial_group",),
                (),
            )
            group = self._new_group(group_id, incident)
            try:
                selected = self.correlations.create_group(group)
            except Exception:
                selected = self.correlations.get_group(incident.tenant_id, incident.environment, group_id)
                if selected is None:
                    raise
        assert decision is not None or existing is not None
        canonical_decision_id = deterministic_id(
            "correlation-decision",
            [
                incident.tenant_id,
                incident.environment,
                incident.id,
                revision,
                selected.group.id,
                V1_POLICY.name,
                V1_POLICY.version,
                V1_POLICY.canonical_hash,
            ],
        )
        if decision is None:
            # Same incident revision was already associated; downstream replay is harmless.
            decision = CorrelationDecision(
                canonical_decision_id,
                "attach",
                incident.id,
                selected.group.id,
                V1_POLICY.name,
                V1_POLICY.version,
                V1_POLICY.canonical_hash,
                datetime.now(timezone.utc),
                selected.group.confidence,
                selected.group.confidence,
                (),
                ("existing_membership",),
                (),
            )
        elif decision.action != "create":
            decision = replace(decision, decision_id=canonical_decision_id)
        appended = self.correlations.append_decision(incident.tenant_id, incident.environment, decision)
        if appended and incident.id not in selected.group.member_incident_ids:
            selected = self._attach_with_occ(selected, incident, decision)
        flood = self._evaluate_flood(selected.group, incident, revision)
        return {
            "status": "complete",
            "correlation": {
                "status": "replayed" if not appended else "complete",
                "group_id": selected.group.id,
                "decision_id": decision.decision_id,
            },
            "flood_control": flood,
            "notification_decision": flood["notification_decision"],
        }

    def defer(self, incident: Incident, phase: str) -> bool:
        revision = str(incident.seq_no or 0)
        op = deterministic_id(
            "incident-runtime-deferred", [incident.tenant_id, incident.environment, incident.id, revision, phase]
        )
        return self.correlations.record_deferred(
            DeferredEvaluation(
                op, incident.tenant_id, incident.environment, incident.id, revision, phase, datetime.now(timezone.utc)
            )
        )

    def reconcile(self, *, limit: int = 50) -> dict[str, int]:
        completed = failed = 0
        for item in self.correlations.list_deferred(limit=min(limit, 100)):
            incident = self.incidents.get_incident(item.tenant_id, item.incident_id, item.environment)
            if not incident:
                failed += 1
                continue
            try:
                self.process(incident)
                self.correlations.mark_reconciled(item.operation_id, datetime.now(timezone.utc))
                completed += 1
            except Exception:
                failed += 1
        return {"completed": completed, "failed": failed}

    def _new_group(self, group_id: str, incident: Incident) -> CorrelationGroup:
        observed = incident.last_observed_at or datetime.now(timezone.utc)
        return CorrelationGroup(
            group_id,
            incident.tenant_id,
            incident.environment,
            V1_POLICY.version,
            incident.id,
            [incident.id],
            1,
            incident.occurrence_count,
            incident.first_observed_at or observed,
            observed,
            str(incident.severity),
            1.0,
            ["initial_group"],
            1.0,
            metadata={
                "policy_name": V1_POLICY.name,
                "policy_hash": V1_POLICY.canonical_hash,
                "affected_assets": sorted(set(incident.affected_assets)),
                "data_product_ids": sorted(set(incident.data_product_ids)),
                "business_services": sorted(set(incident.business_services)),
            },
        )

    def _attach_with_occ(self, selected: StoredGroup, incident: Incident, decision: CorrelationDecision) -> StoredGroup:
        for _ in range(MAX_OCC_RETRIES):
            group = selected.group
            members = sorted(set(group.member_incident_ids + [incident.id]))
            group.member_incident_ids = members[:100]
            group.total_member_count += 1
            group.members_truncated = group.total_member_count > len(group.member_incident_ids)
            group.total_occurrence_count += incident.occurrence_count
            group.first_observed_at = min(
                group.first_observed_at, incident.first_observed_at or group.first_observed_at
            )
            group.last_observed_at = max(group.last_observed_at, incident.last_observed_at or group.last_observed_at)
            if _SEVERITY.get(str(incident.severity), 0) > _SEVERITY.get(group.highest_severity, 0):
                group.highest_severity = str(incident.severity)
            group.confidence = max(group.confidence, decision.confidence)
            for key, values in (
                ("affected_assets", incident.affected_assets),
                ("data_product_ids", incident.data_product_ids),
                ("business_services", incident.business_services),
            ):
                group.metadata[key] = sorted(set(group.metadata.get(key, [])) | set(values))[:100]
            group.updated_at = datetime.now(timezone.utc)
            try:
                return self.correlations.update_group(selected)
            except Exception:
                current = self.correlations.get_group(incident.tenant_id, incident.environment, group.id)
                if current and incident.id in current.group.member_incident_ids:
                    return current
                if current:
                    selected = current
        raise RuntimeError("correlation OCC retry exhausted")

    def _evaluate_flood(self, group: CorrelationGroup, incident: Incident, revision: str) -> dict[str, Any]:
        flood_id = deterministic_id(
            "incident-flood", [incident.tenant_id, incident.environment, group.id, V1_FLOOD_POLICY.version]
        )
        stored = self.floods.get_window(incident.tenant_id, incident.environment, flood_id)
        if stored is None:
            stored = StoredFlood(
                FloodWindow(flood_id, incident.tenant_id, incident.environment, group.id),
                {
                    "representative_incident_id": group.representative_incident_id,
                    "policy_version": V1_FLOOD_POLICY.version,
                    "highest_severity": group.highest_severity,
                    "total_occurrence_count": group.total_occurrence_count,
                },
                0,
                1,
            )
        event_id = deterministic_id(
            "flood-event",
            [incident.tenant_id, incident.environment, incident.id, revision, flood_id, V1_FLOOD_POLICY.version],
        )
        event = FloodEvent(
            event_id,
            incident.last_observed_at or datetime.now(timezone.utc),
            incident.id,
            incident.affected_assets[0] if incident.affected_assets else None,
            incident.correlation_key,
            str(incident.severity),
            business_services=tuple(incident.business_services),
            data_products=tuple(incident.data_product_ids),
        )
        decision, window = evaluate_flood(stored.window, event, V1_FLOOD_POLICY)
        updated = replace(
            stored,
            window=window,
            projection={
                **stored.projection,
                "highest_severity": group.highest_severity,
                "total_occurrence_count": group.total_occurrence_count,
            },
        )
        try:
            updated = (
                self.floods.create_window(updated)
                if self.floods.get_window(incident.tenant_id, incident.environment, flood_id) is None
                else self.floods.update_window(updated)
            )
        except Exception:
            current = self.floods.get_window(incident.tenant_id, incident.environment, flood_id)
            if not current or event_id not in current.window.events:
                raise
            updated = current
        transition_id = deterministic_id(
            "flood-transition",
            [flood_id, event_id, decision.prior_state.value, decision.new_state.value, V1_FLOOD_POLICY.version],
        )
        self.floods.append_transition(incident.tenant_id, incident.environment, transition_id, flood_id, decision)
        notification_id = deterministic_id(
            "notification-decision", [flood_id, event_id, decision.notification_decision, V1_FLOOD_POLICY.version]
        )
        notification = NotificationDecision(
            notification_id,
            flood_id,
            group.id,
            group.representative_incident_id,
            decision.notification_decision,
            decision.reason_codes,
            V1_FLOOD_POLICY.version,
            decision.window_end,
            decision.window_end,
            notification_id,
        )
        self.floods.append_notification(incident.tenant_id, incident.environment, notification)
        return {
            "status": "complete",
            "flood_id": flood_id,
            "state": updated.window.state.value,
            "notification_decision": {
                "status": "eligible",
                "decision_id": notification_id,
                "action": decision.notification_decision,
                "reason_codes": list(decision.reason_codes),
                "delivery_status": "not_attempted",
            },
        }
