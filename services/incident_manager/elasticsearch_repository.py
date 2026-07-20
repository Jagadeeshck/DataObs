from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

from packages.domain_model.incident import Finding, Incident

FINDINGS_ALIAS = "dataobs-findings"
INCIDENTS_ALIAS = "dataobs-incidents"
MAX_PAGE_SIZE = 200


class ElasticsearchIncidentRepository:
    """Durable repository with fixed aliases and mandatory tenancy predicates."""

    def __init__(self, client: Elasticsearch) -> None:
        self.client = client

    @staticmethod
    def _scope(tenant_id: str, environment: str | None = None) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"tenant_id": tenant_id}}]
        if environment is not None:
            filters.append({"term": {"environment": environment}})
        return filters

    def save_finding(self, finding: Finding) -> Finding:
        self.client.index(
            index=FINDINGS_ALIAS,
            id=finding.id,
            document=finding.model_dump(mode="json"),
            op_type="create",
            refresh="wait_for",
        )
        return finding

    def save_incident(self, incident: Incident) -> Incident:
        kwargs: dict[str, Any] = {}
        if incident.seq_no is not None and incident.primary_term is not None:
            kwargs.update(if_seq_no=incident.seq_no, if_primary_term=incident.primary_term)
        response = self.client.index(
            index=INCIDENTS_ALIAS,
            id=incident.id,
            document=incident.model_dump(mode="json", exclude={"seq_no", "primary_term"}),
            refresh="wait_for",
            **kwargs,
        )
        incident.seq_no = response.get("_seq_no")
        incident.primary_term = response.get("_primary_term")
        return incident

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
        result = self._get(FINDINGS_ALIAS, Finding, tenant_id, finding_id, environment)
        return result if isinstance(result, Finding) else None

    def get_incident(self, tenant_id: str, incident_id: str, environment: str | None = None) -> Incident | None:
        result = self._get(INCIDENTS_ALIAS, Incident, tenant_id, incident_id, environment)
        return result if isinstance(result, Incident) else None

    def _search(
        self, alias: str, model: type[Finding] | type[Incident], tenant_id: str, environment: str | None = None
    ) -> list[Any]:
        response = self.client.search(
            index=alias,
            size=MAX_PAGE_SIZE,
            query={"bool": {"filter": self._scope(tenant_id, environment)}},
            sort=[{"updated_at": "desc"}, {"_id": "asc"}],
        )
        return [model.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    def list_findings(self, tenant_id: str, environment: str | None = None) -> list[Finding]:
        return self._search(FINDINGS_ALIAS, Finding, tenant_id, environment)

    def list_incidents(self, tenant_id: str, environment: str | None = None) -> list[Incident]:
        return self._search(INCIDENTS_ALIAS, Incident, tenant_id, environment)

    def find_incident_by_dedup(self, tenant_id: str, deduplication_key: str) -> Incident | None:
        response = self.client.search(
            index=INCIDENTS_ALIAS,
            size=1,
            query={"bool": {"filter": self._scope(tenant_id) + [{"term": {"deduplication_key": deduplication_key}}]}},
        )
        hits = response["hits"]["hits"]
        return Incident.model_validate(hits[0]["_source"]) if hits else None
