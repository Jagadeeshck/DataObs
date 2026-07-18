from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

from .filters import isolation_filters, time_filter


class ElasticsearchConsoleRepository:
    """Bounded, tenant-isolated access to durable Console projections."""

    def __init__(self, es: Elasticsearch):
        self.es = es

    def _search(
        self, index: str, tenant: str, environment: str, *, size: int = 500, **kwargs: Any
    ) -> list[dict[str, Any]]:
        predicates = isolation_filters(tenant, environment, kwargs.pop("source", None))
        period = time_filter(kwargs.pop("start", None), kwargs.pop("end", None))
        if period:
            predicates.append(period)
        response = self.es.search(index=index, query={"bool": {"filter": predicates}}, size=size, **kwargs)
        return [hit["_source"] | {"_id": hit["_id"]} for hit in response["hits"]["hits"]]

    def command_center(
        self, tenant: str, environment: str, start: datetime | None, end: datetime | None
    ) -> dict[str, Any]:
        docs = self._search(
            "dataobs-command-center-summary-v1-read",
            tenant,
            environment,
            size=1,
            start=start,
            end=end,
            sort=[{"@timestamp": "desc"}],
        )
        if docs:
            return docs[0]
        return {
            "tenant_id": tenant,
            "environment": environment,
            "overall_health": "unknown",
            "pillars": [],
            "priority_items": [],
            "recent_changes": [],
            "data_status": {
                "complete": False,
                "warnings": ["No command-center projection is available"],
                "sources": [],
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def topology(
        self, tenant: str, environment: str, *, max_nodes: int, max_edges: int, source: str | None = None
    ) -> dict[str, Any]:
        nodes = self._search(
            "dataobs-pathway-nodes-v1-read", tenant, environment, size=max_nodes, source=source, sort=[{"id": "asc"}]
        )
        edges = self._search(
            "dataobs-pathway-definitions-v1-read",
            tenant,
            environment,
            size=max_edges,
            source=source,
            sort=[{"id": "asc"}],
        )
        node_ids = {str(node.get("id", node.get("node_id", node["_id"]))) for node in nodes}
        edges = [
            edge
            for edge in edges
            if str(edge.get("source_node_id")) in node_ids and str(edge.get("destination_node_id")) in node_ids
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "truncated": len(nodes) == max_nodes or len(edges) == max_edges,
            "data_status": {
                "complete": True,
                "warnings": [],
                "sources": ["elasticsearch"],
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def entity(self, tenant: str, environment: str, entity_id: str) -> dict[str, Any] | None:
        for index in ("dataobs-pathway-nodes-v1-read", "dataobs-assets-v1-read", "dataobs-kafka-topics-v1-read"):
            try:
                result = self.es.get(index=index, id=entity_id)
            except NotFoundError:
                continue
            source = result.get("_source", {})
            if source.get("tenant_id") == tenant and source.get("environment") == environment:
                return source | {"id": entity_id}
        return None

    def save_view(
        self, tenant: str, principal: str, view_id: str, document: dict[str, Any], revision: int = 1
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        saved = document | {
            "id": view_id,
            "tenant_id": tenant,
            "owner_principal": principal,
            "revision": revision,
            "updated_at": now,
            "created_at": document.get("created_at", now),
            "schema_version": "1",
        }
        self.es.index(index="dataobs-saved-views-v1-write", id=view_id, document=saved, refresh="wait_for")
        return saved

    def list_views(self, tenant: str, principal: str) -> list[dict[str, Any]]:
        return self._search("dataobs-saved-views-v1-read", tenant, "*", size=100, sort=[{"updated_at": "desc"}])
