from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from elasticsearch import Elasticsearch


class ElasticsearchPathwayRepository:
    """Incremental trace reader and durable topology writer using PIT/search-after."""

    def __init__(self, es: Elasticsearch, tenant_id: str, environment: str, source_streams: list[str]):
        self.es, self.tenant_id, self.environment = es, tenant_id, environment
        self.source_streams = source_streams

    @property
    def checkpoint_id(self) -> str:
        return f"{self.tenant_id}:{self.environment}:pathway-worker"

    def checkpoint(self) -> dict[str, Any] | None:
        response = self.es.get(index="dataobs-pathway-checkpoints-v1-read", id=self.checkpoint_id, ignore=[404])
        return response.get("_source", {}).get("document") if response.get("found") else None

    def read_spans(
        self, *, after: list[Any] | None, since: str, size: int = 500
    ) -> tuple[list[dict[str, Any]], list[Any] | None]:
        pit = self.es.open_point_in_time(index=",".join(self.source_streams), keep_alive="1m")["id"]
        try:
            request: dict[str, Any] = {
                "pit": {"id": pit, "keep_alive": "1m"},
                "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": since}}}]}},
                "sort": [{"@timestamp": "asc"}, {"_shard_doc": "asc"}],
                "size": size,
            }
            if after:
                request["search_after"] = after
            response = self.es.search(**request)
            hits = response["hits"]["hits"]
            return [h["_source"] | {"_source_document_id": h["_id"]} for h in hits], (
                hits[-1]["sort"] if hits else after
            )
        finally:
            self.es.close_point_in_time(id=pit)

    def save(self, edges: list[dict[str, Any]], cursor: list[Any] | None, worker_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        base = {"tenant_id": self.tenant_id, "environment": self.environment, "updated_at": now}
        for edge in edges:
            self.es.index(
                index="dataobs-pathway-definitions-v1-write",
                id=edge["id"],
                document=base
                | {
                    "id": edge["id"],
                    "source_node_id": edge["source_node_id"],
                    "destination_node_id": edge["destination_node_id"],
                    "pathway_type": edge["pathway_type"],
                    "document": edge,
                },
            )
            self.es.index(
                index="metrics-dataobs.pathway_edge-default",
                document=base
                | {
                    "@timestamp": now,
                    "event_type": "pathway_edge",
                    "edge_id": edge["id"],
                    "source_node_id": edge["source_node_id"],
                    "destination_node_id": edge["destination_node_id"],
                    "pathway_type": edge["pathway_type"],
                    "source_document_ref": edge.get("source_document_ref"),
                },
            )
        checkpoint = {"cursor": cursor, "worker_id": worker_id, "last_successful_collection": now}
        self.es.index(
            index="dataobs-pathway-checkpoints-v1-write",
            id=self.checkpoint_id,
            document=base | {"id": "pathway-worker", "document": checkpoint},
            refresh="wait_for",
        )

    def status(self) -> dict[str, Any]:
        return {"tenant_id": self.tenant_id, "environment": self.environment, "checkpoint": self.checkpoint()}


def replay_start(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
