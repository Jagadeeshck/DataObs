from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from packages.domain_model.incident import Finding, Incident


class IncidentRepository(Protocol):
    """Tenant-scoped persistence contract used by the incident service."""

    def save_finding(self, finding: Finding) -> Finding: ...
    def find_incident_by_dedup(self, tenant_id: str, deduplication_key: str) -> Incident | None: ...
    def save_incident(self, incident: Incident) -> Incident: ...
    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]: ...
    def get_finding(self, tenant_id: str, finding_id: str, environment: str | None = None) -> Finding | None: ...
    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]: ...
    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None: ...


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self.findings: dict[str, Finding] = {}
        self.incidents: dict[str, Incident] = {}
        self.events: list[dict[str, Any]] = []
        self.actions: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

    def save_finding(self, finding: Finding) -> Finding:
        self.findings[finding.id] = finding
        return finding

    def find_incident_by_dedup(self, tenant_id: str, deduplication_key: str) -> Incident | None:
        return next(
            (
                i
                for i in self.incidents.values()
                if i.tenant_id == tenant_id and i.deduplication_key == deduplication_key
            ),
            None,
        )

    def save_incident(self, incident: Incident) -> Incident:
        incident.updated_at = datetime.now(timezone.utc)
        self.incidents[incident.id] = incident
        return incident

    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]:
        return [
            f
            for f in self.findings.values()
            if f.tenant_id == tenant_id and (environment is None or f.environment == environment)
        ]

    def get_finding(self, tenant_id: str, finding_id: str, environment: str | None = None) -> Finding | None:
        f = self.findings.get(finding_id)
        return f if f and f.tenant_id == tenant_id and (environment is None or f.environment == environment) else None

    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]:
        return [
            i
            for i in self.incidents.values()
            if i.tenant_id == tenant_id and (environment is None or i.environment == environment)
        ]

    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None:
        i = self.incidents.get(incident_id)
        return i if i and i.tenant_id == tenant_id and (environment is None or i.environment == environment) else None
