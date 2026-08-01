from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol

from packages.domain_model.incident import Finding, Incident

from .workbench_contracts import IncidentInboxFilters, IncidentInboxPage, TimelinePage


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
    def search_incidents(
        self,
        tenant_id: str,
        environment: str,
        filters: IncidentInboxFilters,
        sort: str,
        page_size: int,
        search_after: list[Any] | None,
        pit_id: str | None,
    ) -> IncidentInboxPage: ...
    def search_events(
        self, tenant_id: str, environment: str, incident_id: str, page_size: int, search_after: list[Any] | None
    ) -> TimelinePage: ...
    def get_operation(self, operation_id: str) -> dict[str, Any] | None: ...
    def save_operation(self, operation_id: str, fingerprint: str, event: dict[str, Any]) -> None: ...


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self.findings: dict[str, Finding] = {}
        self.incidents: dict[str, Incident] = {}
        self.events: list[dict[str, Any]] = []
        self.actions: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.operations: dict[str, dict[str, Any]] = {}

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

    def search_incidents(
        self,
        tenant_id: str,
        environment: str,
        filters: IncidentInboxFilters,
        sort: str,
        page_size: int,
        search_after: list[Any] | None,
        pit_id: str | None,
    ) -> IncidentInboxPage:
        values = [i for i in self.list_incidents(tenant_id, environment) if _matches(i, filters)]
        values.sort(key=lambda item: _incident_sort(item, sort))
        if search_after is not None:
            values = [item for item in values if list(_incident_sort(item, sort)) > search_after]
        page = values[: page_size + 1]
        more = len(page) > page_size
        page = page[:page_size]
        return IncidentInboxPage(page, list(_incident_sort(page[-1], sort)) if more else None, pit_id or "memory-pit")

    def search_events(
        self, tenant_id: str, environment: str, incident_id: str, page_size: int, search_after: list[Any] | None
    ) -> TimelinePage:
        events = self.list_events(tenant_id, environment, incident_id)
        if search_after:
            events = [event for event in events if [event["timestamp"], event["event_id"]] > search_after]
        page = events[: page_size + 1]
        more = len(page) > page_size
        page = page[:page_size]
        return TimelinePage(page, [page[-1]["timestamp"], page[-1]["event_id"]] if more else None)

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        return deepcopy(self.operations.get(operation_id))

    def save_operation(self, operation_id: str, fingerprint: str, event: dict[str, Any]) -> None:
        existing = self.operations.get(operation_id)
        if existing and existing["fingerprint"] != fingerprint:
            raise VersionConflict("idempotency key was used for another operation")
        self.operations[operation_id] = {"fingerprint": fingerprint, "event": deepcopy(event)}


def _matches(item: Incident, f: IncidentInboxFilters) -> bool:
    text = f.search.casefold()
    return (
        (not f.state or str(item.incident_state) == f.state)
        and (not f.severity or str(item.severity) == f.severity)
        and (not f.owner or item.owner_team == f.owner)
        and (not f.business_service or item.business_service == f.business_service)
        and (not f.asset or f.asset in item.affected_assets)
        and (not f.unassigned or not item.owner_team)
        and (not f.opened_from or bool(item.opened_at and item.opened_at >= f.opened_from))
        and (not f.opened_to or bool(item.opened_at and item.opened_at <= f.opened_to))
        and (not f.observed_from or bool(item.last_observed_at and item.last_observed_at >= f.observed_from))
        and (not f.observed_to or bool(item.last_observed_at and item.last_observed_at <= f.observed_to))
        and (not text or text in " ".join([item.title, item.impact_summary or "", *item.affected_assets]).casefold())
    )


def _incident_sort(item: Incident, sort: str) -> tuple[Any, ...]:
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    if sort == "severity":
        return ({"critical": 0, "high": 1, "medium": 2, "low": 3}[str(item.severity)], item.id)
    if sort == "newest_opened":
        return (-(item.opened_at or epoch).timestamp(), item.id)
    if sort == "occurrence_count":
        return (-item.occurrence_count, item.id)
    return (-(item.last_observed_at or epoch).timestamp(), item.id)
