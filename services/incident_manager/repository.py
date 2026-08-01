from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol

from packages.domain_model.incident import Finding, Incident


def finding_projection(finding: Finding) -> dict[str, Any]:
    """Comparable durable finding content, excluding write bookkeeping."""
    return finding.model_dump(mode="json", exclude={"created_at", "updated_at"})


class VersionConflict(RuntimeError):
    """A stable domain error for create or optimistic-concurrency conflicts."""


class IncidentRepository(Protocol):
    """Tenant-scoped persistence contract used by the incident service."""

    actions: dict[str, dict[str, Any]]
    approvals: dict[str, dict[str, Any]]

    def save_finding(self, finding: Finding) -> Finding: ...
    def find_incident_by_dedup(self, tenant_id: str, environment: str, deduplication_key: str) -> Incident | None: ...
    def create_incident(self, incident: Incident) -> Incident: ...
    def update_incident(self, incident: Incident) -> Incident: ...
    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]: ...
    def get_finding(self, tenant_id: str, finding_id: str, environment: str | None = None) -> Finding | None: ...
    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]: ...
    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None: ...
    def append_event(self, event: dict[str, Any]) -> None: ...
    def list_events(self, tenant_id: str, environment: str, incident_id: str) -> list[dict[str, Any]]: ...


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self.findings: dict[str, Finding] = {}
        self.incidents: dict[str, Incident] = {}
        self.events: list[dict[str, Any]] = []
        self.actions: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

    def save_finding(self, finding: Finding) -> Finding:
        current = self.findings.get(finding.id)
        if current is not None:
            if (current.tenant_id, current.environment) != (finding.tenant_id, finding.environment):
                raise ValueError("finding identity scope is immutable")
            if finding.last_observed_at < current.last_observed_at:
                return deepcopy(current)
            if finding.last_observed_at == current.last_observed_at and finding_projection(
                finding
            ) == finding_projection(current):
                return deepcopy(current)
        self.findings[finding.id] = deepcopy(finding)
        return finding

    def find_incident_by_dedup(self, tenant_id: str, environment: str, deduplication_key: str) -> Incident | None:
        return next(
            (
                i
                for i in self.incidents.values()
                if i.tenant_id == tenant_id
                and i.environment == environment
                and i.deduplication_key == deduplication_key
            ),
            None,
        )

    def create_incident(self, incident: Incident) -> Incident:
        if incident.id in self.incidents:
            raise VersionConflict("incident version conflict")
        incident.updated_at = datetime.now(timezone.utc)
        incident.seq_no, incident.primary_term = 0, 1
        self.incidents[incident.id] = deepcopy(incident)
        return incident

    def update_incident(self, incident: Incident) -> Incident:
        current = self.incidents.get(incident.id)
        if (
            current is None
            or incident.seq_no is None
            or incident.primary_term is None
            or (incident.seq_no, incident.primary_term) != (current.seq_no, current.primary_term)
        ):
            raise VersionConflict("incident version conflict")
        incident.updated_at = datetime.now(timezone.utc)
        incident.seq_no += 1
        self.incidents[incident.id] = deepcopy(incident)
        return incident

    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]:
        return deepcopy(
            [
                f
                for f in self.findings.values()
                if f.tenant_id == tenant_id and (environment is None or f.environment == environment)
            ]
        )

    def get_finding(self, tenant_id: str, finding_id: str, environment: str | None = None) -> Finding | None:
        f = self.findings.get(finding_id)
        return (
            deepcopy(f)
            if f and f.tenant_id == tenant_id and (environment is None or f.environment == environment)
            else None
        )

    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]:
        return deepcopy(
            [
                i
                for i in self.incidents.values()
                if i.tenant_id == tenant_id and (environment is None or i.environment == environment)
            ]
        )

    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None:
        i = self.incidents.get(incident_id)
        return (
            deepcopy(i)
            if i and i.tenant_id == tenant_id and (environment is None or i.environment == environment)
            else None
        )

    def append_event(self, event: dict[str, Any]) -> None:
        if any(item["event_id"] == event["event_id"] for item in self.events):
            return
        self.events.append(deepcopy(event))

    def list_events(self, tenant_id: str, environment: str, incident_id: str) -> list[dict[str, Any]]:
        return deepcopy(
            sorted(
                (
                    item
                    for item in self.events
                    if item["tenant_id"] == tenant_id
                    and item["environment"] == environment
                    and item["incident_id"] == incident_id
                ),
                key=lambda item: (item["timestamp"], item["event_id"]),
            )
        )
