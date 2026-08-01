from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.pathways.intelligence import assemble_pathways
from packages.pathways.span_normalizer import normalize_span

from .repository import ElasticsearchPathwayRepository
from .topology_builder import projections_from_span


class PathwayWorkerService:
    def __init__(
        self,
        repository: ElasticsearchPathwayRepository,
        *,
        late_arrival_seconds: int = 300,
        worker_id: str | None = None,
    ):
        self.repository, self.late_arrival_seconds = repository, late_arrival_seconds
        self.worker_id = worker_id or str(uuid.uuid4())

    def process_once(self, *, replay_since: str | None = None) -> dict[str, Any]:
        token = self.repository.acquire_lease(self.worker_id)
        try:
            checkpoint = self.repository.checkpoint() or {}
            if replay_since:
                since = replay_since
            elif checkpoint.get("last_event_timestamp"):
                since = (
                    datetime.fromisoformat(checkpoint["last_event_timestamp"])
                    - timedelta(seconds=self.late_arrival_seconds)
                ).isoformat()
            else:
                since = (datetime.now(timezone.utc) - timedelta(seconds=self.late_arrival_seconds)).isoformat()
            # Overlap replay always starts at its timestamp boundary. Observation IDs
            # deduplicate previously committed events.
            spans, position = self.repository.read_spans(after=None, since=since)
            edges: dict[str, dict[str, Any]] = {}
            nodes: dict[str, dict[str, Any]] = {}
            for source in spans:
                span = normalize_span(source) | {"_source_document_id": source.get("_source_document_id")}
                if span.get("messaging.system") != "kafka" or not span.get("messaging.destination.name"):
                    continue
                projected_nodes, edge = projections_from_span(
                    span, self.repository.tenant_id, self.repository.environment
                )
                edges[edge["edge_id"]] = edge
                nodes.update({node["node_id"]: node for node in projected_nodes})
            pathways = assemble_pathways(list(nodes.values()), list(edges.values()))
            self.repository.save(
                list(edges.values()),
                position,
                self.worker_id,
                token,
                len(spans),
                nodes=list(nodes.values()),
                pathways=pathways,
            )
            return {
                "spans_read": len(spans),
                "nodes_projected": len(nodes),
                "edges_written": len(edges),
                "pathways_updated": len(pathways),
                "last_event_position": position,
                "late_arrival_overlap_seconds": self.late_arrival_seconds,
                "fencing_token": token,
            }
        finally:
            self.repository.release_lease(self.worker_id, token)
