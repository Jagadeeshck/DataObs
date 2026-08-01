from __future__ import annotations

from typing import Any

from elasticsearch import ConflictError, Elasticsearch, NotFoundError

from packages.domain_model.incident import Finding, Incident

from .repository import VersionConflict, finding_projection

FINDINGS_ALIAS = "dataobs-findings-v1-write"
FINDINGS_READ_ALIAS = "dataobs-findings-v1-read"
INCIDENTS_ALIAS = "dataobs-incidents-v1-write"
INCIDENTS_READ_ALIAS = "dataobs-incidents-v1-read"
MAX_PAGE_SIZE = 200
TIMELINE_STREAM = "logs-dataobs.incident_comment-default"


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
            self.client.create(index=TIMELINE_STREAM, id=event["event_id"], document=event, refresh="wait_for")
        except ConflictError:
            # Idempotent retries never rewrite the existing historical event.
            return

    def list_events(self, tenant_id: str, environment: str, incident_id: str) -> list[dict[str, Any]]:
        response = self.client.search(
            index="logs-dataobs.incident_comment-*",
            size=MAX_PAGE_SIZE,
            query={"bool": {"filter": self._scope(tenant_id, environment) + [{"term": {"incident_id": incident_id}}]}},
            sort=[{"timestamp": "asc"}, {"event_id": "asc"}],
        )
        return [dict(hit["_source"]) for hit in response["hits"]["hits"]]
