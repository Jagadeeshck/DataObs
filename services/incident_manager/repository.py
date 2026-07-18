from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Finding, Incident


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

    def list_findings(self, tenant_id: str) -> list[Finding]:
        return [f for f in self.findings.values() if f.tenant_id == tenant_id]

    def get_finding(self, tenant_id: str, finding_id: str) -> Finding | None:
        f = self.findings.get(finding_id)
        return f if f and f.tenant_id == tenant_id else None

    def list_incidents(self, tenant_id: str) -> list[Incident]:
        return [i for i in self.incidents.values() if i.tenant_id == tenant_id]

    def get_incident(self, tenant_id: str, incident_id: str) -> Incident | None:
        i = self.incidents.get(incident_id)
        return i if i and i.tenant_id == tenant_id else None
