from __future__ import annotations

from typing import Any

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.incident import Finding, Incident

from .repository import VersionConflict, finding_projection
from .timeline_storage import timeline_document_to_event, timeline_event_to_document
from .workbench_contracts import IncidentInboxFilters, IncidentInboxPage, TimelinePage

FINDINGS_ALIAS = "dataobs-findings-v1-write"
FINDINGS_READ_ALIAS = "dataobs-findings-v1-read"
INCIDENTS_ALIAS = "dataobs-incidents-v1-write"
INCIDENTS_READ_ALIAS = "dataobs-incidents-v1-read"
MAX_PAGE_SIZE = 200
TIMELINE_STREAM = "logs-dataobs.incident_comment-default"
IDEMPOTENCY_ALIAS = "dataobs-action-idempotency-v1-write"
IDEMPOTENCY_READ_ALIAS = "dataobs-action-idempotency-v1-read"


class ElasticsearchIncidentRepository:
    """Durable repository with fixed aliases and mandatory tenancy predicates."""

    def __init__(self, client: Elasticsearch) -> None:
        self.client = client
        # Action execution is deliberately disabled; these compatibility stores
        # contain preview/approval state only until a durable adapter exists.
        self.actions: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _scope(tenant_id: str, environment: str | None = None) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"tenant_id": tenant_id}}]
        if environment is not None:
            filters.append({"term": {"environment": environment}})
        return filters

    def save_finding(self, finding: Finding) -> Finding:
        # The deterministic ID makes this a small compare-and-set register. Newer
        # observations win; stale replays return the durable value unchanged.
        for _ in range(3):
            try:
                current = self.client.get(index=FINDINGS_READ_ALIAS, id=finding.id)
            except NotFoundError:
                try:
                    self.client.index(
                        index=FINDINGS_ALIAS,
                        id=finding.id,
                        document=finding.model_dump(mode="json"),
                        op_type="create",
                        refresh="wait_for",
                    )
                    return finding
                except ConflictError:
                    continue
            source = current["_source"]
            stored = Finding.model_validate(source)
            immutable = ("tenant_id", "environment", "source_event_id", "source_event_version", "asset_id")
            if any(getattr(stored, name) != getattr(finding, name) for name in immutable):
                raise ValueError("finding source identity is immutable")
            if finding.last_observed_at < stored.last_observed_at:
                return stored
            incoming = finding.model_dump(mode="json")
            if finding_projection(finding) == finding_projection(stored):
                return stored
            try:
                self.client.index(
                    index=FINDINGS_ALIAS,
                    id=finding.id,
                    document=incoming,
                    if_seq_no=current["_seq_no"],
                    if_primary_term=current["_primary_term"],
                    refresh="wait_for",
                )
                return finding
            except ConflictError:
                continue
        raise VersionConflict("finding version conflict")

    def _write_incident(self, incident: Incident, **kwargs: Any) -> Incident:
        try:
            response = self.client.index(
                index=INCIDENTS_ALIAS,
                id=incident.id,
                document=incident.model_dump(mode="json", exclude={"seq_no", "primary_term"}),
                refresh="wait_for",
                **kwargs,
            )
        except ConflictError as exc:
            raise VersionConflict("incident version conflict") from exc
        incident.seq_no = response.get("_seq_no")
        incident.primary_term = response.get("_primary_term")
        return incident

    def create_incident(self, incident: Incident) -> Incident:
        return self._write_incident(incident, op_type="create")

    def update_incident(self, incident: Incident) -> Incident:
        if incident.seq_no is None or incident.primary_term is None:
            raise VersionConflict("incident update requires concurrency metadata")
        return self._write_incident(incident, if_seq_no=incident.seq_no, if_primary_term=incident.primary_term)

    def _get(
        self,
        alias: str,
        model: type[Finding] | type[Incident],
        tenant_id: str,
        document_id: str,
        environment: str | None = None,
    ) -> Finding | Incident | None:
        try:
            result = self.client.get(index=alias, id=document_id)
        except NotFoundError:
            return None
        source = result["_source"]
        if source.get("tenant_id") != tenant_id or (
            environment is not None and source.get("environment") != environment
        ):
            return None
        (
            source.update(seq_no=result.get("_seq_no"), primary_term=result.get("_primary_term"))
            if model is Incident
            else None
        )
        return model.model_validate(source)

    def get_finding(self, tenant_id: str, finding_id: str, environment: str | None = None) -> Finding | None:
        result = self._get(FINDINGS_READ_ALIAS, Finding, tenant_id, finding_id, environment)
        return result if isinstance(result, Finding) else None

    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None:
        result = self._get(INCIDENTS_READ_ALIAS, Incident, tenant_id, incident_id, environment)
        return result if isinstance(result, Incident) else None

    def _search(
        self, alias: str, model: type[Finding] | type[Incident], tenant_id: str, environment: str | None = None
    ) -> list[Any]:
        response = self.client.search(
            index=alias,
            size=MAX_PAGE_SIZE,
            query={"bool": {"filter": self._scope(tenant_id, environment)}},
            sort=[{"updated_at": "desc"}, {"_id": "asc"}],
            seq_no_primary_term=model is Incident,
        )
        results = []
        for hit in response["hits"]["hits"]:
            source = dict(hit["_source"])
            if model is Incident:
                source.update(seq_no=hit.get("_seq_no"), primary_term=hit.get("_primary_term"))
            results.append(model.model_validate(source))
        return results

    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]:
        return self._search(FINDINGS_READ_ALIAS, Finding, tenant_id, environment)

    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]:
        return self._search(INCIDENTS_READ_ALIAS, Incident, tenant_id, environment)

    def find_incident_by_dedup(self, tenant_id: str, environment: str, deduplication_key: str) -> Incident | None:
        response = self.client.search(
            index=INCIDENTS_READ_ALIAS,
            size=1,
            query={
                "bool": {
                    "filter": self._scope(tenant_id, environment) + [{"term": {"deduplication_key": deduplication_key}}]
                }
            },
            seq_no_primary_term=True,
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        source = dict(hits[0]["_source"])
        source.update(seq_no=hits[0].get("_seq_no"), primary_term=hits[0].get("_primary_term"))
        return Incident.model_validate(source)

    def append_event(self, event: dict[str, Any]) -> None:
        """Append an immutable event to the released incident collaboration stream."""
        try:
            self.client.create(
                index=TIMELINE_STREAM,
                id=event["event_id"],
                document=timeline_event_to_document(event),
                refresh="wait_for",
            )
        except ConflictError:
            # Idempotent retries never rewrite the existing historical event.
            return

    def list_events(self, tenant_id: str, environment: str, incident_id: str) -> list[dict[str, Any]]:
        response = self.client.search(
            index="logs-dataobs.incident_comment-*",
            size=MAX_PAGE_SIZE,
            query={"bool": {"filter": self._scope(tenant_id, environment) + [{"term": {"incident_id": incident_id}}]}},
            sort=[{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        )
        return [timeline_document_to_event(dict(hit["_source"])) for hit in response["hits"]["hits"]]

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
        clauses = self._scope(tenant_id, environment)
        for field, value in (
            ("incident_state", filters.state),
            ("severity", filters.severity),
            ("owner_team", filters.owner),
            ("business_service", filters.business_service),
        ):
            if value:
                clauses.append({"term": {field: value}})
        if filters.asset:
            clauses.append({"term": {"affected_assets": filters.asset}})
        if filters.unassigned:
            clauses.append({"bool": {"must_not": {"exists": {"field": "owner_team"}}}})
        for field, lower, upper in (
            ("opened_at", filters.opened_from, filters.opened_to),
            ("last_observed_at", filters.observed_from, filters.observed_to),
        ):
            bounds = {key: value.isoformat() for key, value in (("gte", lower), ("lte", upper)) if value}
            if bounds:
                clauses.append({"range": {field: bounds}})
        must = []
        if filters.search:
            must.append({"multi_match": {"query": filters.search, "fields": ["title", "impact_summary"]}})
        sorts: dict[str, list[dict[str, Any]]] = {
            "newest_opened": [{"opened_at": "desc"}, {"id": "asc"}],
            "recently_observed": [{"last_observed_at": "desc"}, {"id": "asc"}],
            "occurrence_count": [{"occurrence_count": "desc"}, {"id": "asc"}],
            "severity": [{"severity_rank": "asc"}, {"id": "asc"}],
        }
        body: dict[str, Any] = {
            "size": page_size + 1,
            "query": {"bool": {"filter": clauses, "must": must}},
            "sort": sorts[sort],
            "seq_no_primary_term": True,
        }
        if sort == "severity":
            body["runtime_mappings"] = {
                "severity_rank": {
                    "type": "long",
                    "script": {
                        "source": "def r=['critical':0L,'high':1L,'medium':2L,'low':3L]; emit(r.getOrDefault(doc['severity'].value,4L))"
                    },
                }
            }
        if search_after:
            body["search_after"] = search_after
        if pit_id is None:
            pit_id = self.client.open_point_in_time(index=INCIDENTS_READ_ALIAS, keep_alive="2m")["id"]
        body["pit"] = {"id": pit_id, "keep_alive": "2m"}
        response = self.client.search(**body)
        hits = response["hits"]["hits"]
        more = len(hits) > page_size
        hits = hits[:page_size]
        items = []
        for hit in hits:
            source = dict(hit["_source"])
            source.update(seq_no=hit.get("_seq_no"), primary_term=hit.get("_primary_term"))
            items.append(Incident.model_validate(source))
        return IncidentInboxPage(items, list(hits[-1]["sort"]) if more else None, response.get("pit_id", pit_id))

    def search_events(
        self, tenant_id: str, environment: str, incident_id: str, page_size: int, search_after: list[Any] | None
    ) -> TimelinePage:
        body: dict[str, Any] = {
            "index": "logs-dataobs.incident_comment-*",
            "size": page_size + 1,
            "query": {
                "bool": {"filter": self._scope(tenant_id, environment) + [{"term": {"incident_id": incident_id}}]}
            },
            "sort": [{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        }
        if search_after:
            body["search_after"] = search_after
        hits = self.client.search(**body)["hits"]["hits"]
        more = len(hits) > page_size
        hits = hits[:page_size]
        return TimelinePage(
            [timeline_document_to_event(dict(hit["_source"])) for hit in hits], list(hits[-1]["sort"]) if more else None
        )

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        try:
            result = self.client.get(index=IDEMPOTENCY_READ_ALIAS, id=operation_id)
        except NotFoundError:
            return None
        source = result["_source"]
        document = source.get("document") or {}
        return {"fingerprint": source.get("fingerprint"), "event": document.get("event")}

    def save_operation(self, operation_id: str, fingerprint: str, event: dict[str, Any]) -> None:
        document = {
            "fingerprint": fingerprint,
            "idempotency_key": operation_id,
            "document": {"event": event},
            "@timestamp": event["timestamp"],
            "tenant_id": event["tenant_id"],
            "environment": event["environment"],
        }
        try:
            self.client.create(index=IDEMPOTENCY_ALIAS, id=operation_id, document=document, refresh="wait_for")
        except ConflictError:
            existing = self.get_operation(operation_id)
            if not existing or existing["fingerprint"] != fingerprint:
                raise VersionConflict("idempotency key was used for another operation")
