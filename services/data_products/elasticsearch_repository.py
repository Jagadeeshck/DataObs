"""Elasticsearch Data Product repository with precision-safe reconciliation reads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from services.data_products.elasticsearch_repository_base import *  # noqa: F403
from services.data_products.elasticsearch_repository_base import (
    DEPENDENCIES,
    OPERATIONS,
    ElasticsearchDataProductRepository as _BaseElasticsearchDataProductRepository,
)
from services.data_products.events import ProductConsistencyError
from services.data_products.operation_state import (
    DataProductOperationHistoryEvent,
    DataProductOperationState,
)


class ElasticsearchDataProductRepository(_BaseElasticsearchDataProductRepository):
    """Apply Elasticsearch 9 precision and visibility contracts."""

    def list_reconcilable_operations(
        self,
        tenant_id: str,
        environment: str,
        *,
        limit: int = 100,
        operation_kind: str | None = None,
        now: datetime | None = None,
    ) -> list[DataProductOperationState]:
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        query_now = now or datetime.now(timezone.utc)
        if query_now.tzinfo is None or query_now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        query_now = query_now.astimezone(timezone.utc)
        query_instant = query_now.isoformat()
        filters: list[dict[str, Any]] = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"environment": environment}},
            {"terms": {"outcome": ["pending", "claimed"]}},
            {
                "bool": {
                    "should": [
                        {"term": {"outcome": "pending"}},
                        {"range": {"claim_expires_at": {"lte": query_instant}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            {"exists": {"field": "document.status"}},
            {
                "bool": {
                    "should": [
                        {"bool": {"must_not": {"exists": {"field": "next_attempt_at"}}}},
                        {"range": {"next_attempt_at": {"lte": query_instant}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
        ]
        if operation_kind is not None:
            filters.append({"term": {"action": operation_kind}})

        # Elasticsearch `date` fields use millisecond precision. A broad range
        # can include values a few microseconds in the future, so use the source
        # value for the final eligibility decision and paginate past false hits.
        states: list[DataProductOperationState] = []
        search_after: Sequence[str | int | float] | None = None
        page_size = max(100, limit)
        while len(states) < limit:
            request: dict[str, Any] = {
                "index": OPERATIONS,
                "size": page_size,
                "seq_no_primary_term": True,
                "query": {"bool": {"filter": filters}},
                "sort": [
                    {"next_attempt_at": {"order": "asc", "missing": "_first"}},
                    {"operation_id": "asc"},
                ],
            }
            if search_after is not None:
                request["search_after"] = search_after
            response = self.client.search(**request)
            hits = response["hits"]["hits"]
            if not hits:
                break
            for hit in hits:
                if "status" not in hit["_source"].get("document", {}):
                    continue
                state = self._state_from_hit(hit)
                if state.next_attempt_at is not None and state.next_attempt_at > query_now:
                    continue
                if state.status == "claimed" and (
                    state.claim_expires_at is None or state.claim_expires_at > query_now
                ):
                    continue
                states.append(state)
            if len(states) >= limit or len(hits) < page_size:
                break
            continuation = hits[-1].get("sort")
            if not continuation:
                raise ProductConsistencyError("reconciliation page missing continuation")
            search_after = tuple(continuation)

        minimum = datetime.min.replace(tzinfo=timezone.utc)
        states.sort(
            key=lambda state: (
                state.next_attempt_at is not None,
                state.next_attempt_at or minimum,
                state.operation_id,
            )
        )
        return states[:limit]

    def get_operation_history(self, tenant_id, environment, operation_id, *, limit=100):
        if not 1 <= limit <= 200:
            raise ValueError("limit outside bounds")
        response = self.client.search(
            index=OPERATIONS,
            size=limit,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"operation_id": operation_id}},
                        {"exists": {"field": "document.event_id"}},
                    ]
                }
            },
            sort=[{"occurred_at": "asc"}, {"document.event_id": "asc"}],
        )
        events = []
        for hit in response["hits"]["hits"]:
            value = dict(hit["_source"].get("document", {}))
            if "event_id" not in value:
                continue
            for key in ("occurred_at", "applied_at"):
                if value.get(key):
                    value[key] = datetime.fromisoformat(value[key])
            events.append(DataProductOperationHistoryEvent(**value))
        return sorted(events, key=lambda event: (event.occurred_at, event.event_id))

    def _apply_dependency_chunk(self, tenant_id, environment, product_id, edges, *, tombstone):
        super()._apply_dependency_chunk(tenant_id, environment, product_id, edges, tombstone=tombstone)
        if edges:
            self.client.indices.refresh(index=DEPENDENCIES)
