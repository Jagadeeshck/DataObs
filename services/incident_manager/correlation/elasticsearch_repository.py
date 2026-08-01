from __future__ import annotations

from datetime import datetime
from typing import Any

from elasticsearch import ConflictError, NotFoundError

from .contracts import CorrelationDecision, CorrelationGroup
from .repository import MAX_CANDIDATES, MAX_PAGE_SIZE, CorrelationRepository, DeferredEvaluation, StoredGroup
from .storage import decision_to_api, decision_to_document, document_to_decision, document_to_group, group_to_document

GROUP_ALIAS = "dataobs-incident-correlations-write"
GROUP_READ_ALIAS = "dataobs-incident-correlations-read"
EVENT_STREAM = "logs-dataobs.correlation_event-default"
EVENT_PATTERN = "logs-dataobs.correlation_event-*"


class ElasticsearchCorrelationRepository(CorrelationRepository):
    def __init__(self, client: Any) -> None:
        self.client = client

    @staticmethod
    def _scope(tenant_id: str, environment: str) -> list[dict[str, Any]]:
        return [{"term": {"tenant_id": tenant_id}}, {"term": {"environment": environment}}]

    def create_group(self, group: CorrelationGroup) -> StoredGroup:
        response = self.client.create(
            index=GROUP_ALIAS, id=group.id, document=group_to_document(group), refresh="wait_for"
        )
        return StoredGroup(group, response["_seq_no"], response["_primary_term"])

    def get_group(self, tenant_id: str, environment: str, group_id: str) -> StoredGroup | None:
        try:
            hit = self.client.get(index=GROUP_READ_ALIAS, id=group_id)
        except NotFoundError:
            return None
        group = document_to_group(hit["_source"])
        return (
            StoredGroup(group, hit["_seq_no"], hit["_primary_term"])
            if (group.tenant_id, group.environment) == (tenant_id, environment)
            else None
        )

    def update_group(self, stored: StoredGroup) -> StoredGroup:
        response = self.client.index(
            index=GROUP_ALIAS,
            id=stored.group.id,
            document=group_to_document(stored.group),
            if_seq_no=stored.seq_no,
            if_primary_term=stored.primary_term,
            refresh="wait_for",
        )
        return StoredGroup(stored.group, response["_seq_no"], response["_primary_term"])

    def find_candidate_groups(
        self, tenant_id: str, environment: str, incident: Any, *, limit: int = MAX_CANDIDATES
    ) -> list[StoredGroup]:
        should = []
        for field, values in (
            ("affected_assets", incident.affected_assets),
            ("data_product_ids", incident.data_product_ids),
            ("business_services", incident.business_services),
        ):
            if values:
                should.append({"terms": {field: sorted(set(values))[:100]}})
        if not should:
            return []
        response = self.client.search(
            index=GROUP_READ_ALIAS,
            size=min(limit, MAX_CANDIDATES),
            timeout="2s",
            _source=list(
                sorted(
                    {
                        "id",
                        "tenant_id",
                        "environment",
                        "correlation_id",
                        "correlation_key",
                        "correlation_version",
                        "incident_id",
                        "resource_ids",
                        "affected_assets",
                        "data_product_ids",
                        "business_services",
                        "severity",
                        "confidence",
                        "occurrence_count",
                        "first_observed_at",
                        "last_observed_at",
                        "created_at",
                        "updated_at",
                        "status",
                        "correlation_explanation",
                        "metadata",
                    }
                )
            ),
            query={
                "bool": {
                    "filter": self._scope(tenant_id, environment)
                    + [
                        {"term": {"status": "active"}},
                        {"term": {"correlation_version": "v1"}},
                        {
                            "range": {
                                "last_observed_at": {
                                    "gte": (
                                        incident.last_observed_at.isoformat()
                                        if incident.last_observed_at
                                        else "now-24h"
                                    )
                                }
                            }
                        },
                    ],
                    "should": should,
                    "minimum_should_match": 1,
                }
            },
            sort=[{"last_observed_at": "desc"}, {"correlation_id": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            StoredGroup(document_to_group(hit["_source"]), hit["_seq_no"], hit["_primary_term"])
            for hit in response["hits"]["hits"]
        ]

    def find_group_for_incident(self, tenant_id: str, environment: str, incident_id: str) -> StoredGroup | None:
        response = self.client.search(
            index=EVENT_PATTERN,
            size=1,
            timeout="2s",
            query={
                "bool": {
                    "filter": self._scope(tenant_id, environment)
                    + [{"term": {"incident_id": incident_id}}, {"terms": {"status": ["attach", "create"]}}]
                }
            },
            sort=[{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        )
        hits = response["hits"]["hits"]
        return self.get_group(tenant_id, environment, hits[0]["_source"]["correlation_key"]) if hits else None

    def list_groups(self, tenant_id: str, environment: str, *, limit: int = 25) -> list[StoredGroup]:
        response = self.client.search(
            index=GROUP_READ_ALIAS,
            size=min(limit, MAX_PAGE_SIZE),
            timeout="2s",
            query={"bool": {"filter": self._scope(tenant_id, environment)}},
            sort=[{"last_observed_at": "desc"}, {"correlation_id": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            StoredGroup(document_to_group(hit["_source"]), hit["_seq_no"], hit["_primary_term"])
            for hit in response["hits"]["hits"]
        ]

    def append_decision(self, tenant_id: str, environment: str, decision: CorrelationDecision) -> bool:
        try:
            self.client.create(
                index=EVENT_STREAM,
                id=decision.decision_id,
                document=decision_to_document(tenant_id, environment, decision),
                refresh="wait_for",
            )
            return True
        except ConflictError:
            return False

    def has_decision(self, tenant_id: str, environment: str, decision_id: str) -> bool:
        try:
            hit = self.client.get(index=EVENT_PATTERN, id=decision_id)
        except NotFoundError:
            return False
        return (hit["_source"].get("tenant_id"), hit["_source"].get("environment")) == (tenant_id, environment)

    def list_decisions(
        self, tenant_id: str, environment: str, group_id: str, *, limit: int = MAX_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        response = self.client.search(
            index=EVENT_PATTERN,
            size=min(limit, MAX_PAGE_SIZE),
            timeout="2s",
            query={"bool": {"filter": self._scope(tenant_id, environment) + [{"term": {"correlation_key": group_id}}]}},
            sort=[{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        )
        return [decision_to_api(document_to_decision(hit["_source"])) for hit in response["hits"]["hits"]]

    def record_deferred(self, item: DeferredEvaluation) -> bool:
        document = {
            "@timestamp": item.created_at.isoformat(),
            "tenant_id": item.tenant_id,
            "environment": item.environment,
            "correlation_id": item.operation_id,
            "correlation_key": "deferred",
            "correlation_version": "v1",
            "incident_id": item.incident_id,
            "status": "deferred",
            "reason_code": item.phase,
            "metadata": {"incident_revision": item.incident_revision, "attempt": item.attempt},
        }
        try:
            self.client.create(index=EVENT_STREAM, id=item.operation_id, document=document, refresh="wait_for")
            return True
        except ConflictError:
            return False

    def list_deferred(self, *, limit: int) -> list[DeferredEvaluation]:
        response = self.client.search(
            index=EVENT_PATTERN,
            size=min(limit, 100),
            timeout="2s",
            query={"term": {"status": "deferred"}},
            sort=[{"@timestamp": "asc"}, {"correlation_id": "asc"}],
        )
        return [
            DeferredEvaluation(
                hit["_source"]["correlation_id"],
                hit["_source"]["tenant_id"],
                hit["_source"]["environment"],
                hit["_source"]["incident_id"],
                str(hit["_source"].get("metadata", {}).get("incident_revision", "0")),
                hit["_source"]["reason_code"],
                datetime.fromisoformat(hit["_source"]["@timestamp"]),
            )
            for hit in response["hits"]["hits"]
        ]

    def mark_reconciled(self, operation_id: str, completed_at: datetime) -> None:
        self.client.update(
            index=EVENT_PATTERN,
            id=operation_id,
            doc={"status": "reconciled", "updated_at": completed_at.isoformat()},
            refresh="wait_for",
        )
