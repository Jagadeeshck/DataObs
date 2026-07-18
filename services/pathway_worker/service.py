from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.pathways.span_normalizer import normalize_span

from .repository import ElasticsearchPathwayRepository
from .topology_builder import edge_from_span


class PathwayWorkerService:
    def __init__(
        self,
        repository: ElasticsearchPathwayRepository,
        *,
        late_arrival_seconds: int = 300,
        worker_id: str | None = None,
    ):
        self.repository = repository
        self.late_arrival_seconds = late_arrival_seconds
        self.worker_id = worker_id or str(uuid.uuid4())

    def process_once(self, *, replay_since: str | None = None) -> dict[str, Any]:
        checkpoint = self.repository.checkpoint() or {}
        since = (
            replay_since
            or checkpoint.get("since")
            or (datetime.now(timezone.utc) - timedelta(seconds=self.late_arrival_seconds)).isoformat()
        )
        spans, cursor = self.repository.read_spans(
            after=None if replay_since else checkpoint.get("cursor"), since=since
        )
        edges: dict[str, dict[str, Any]] = {}
        for source in spans:
            span = normalize_span(source)
            if span.get("messaging.system") != "kafka" or not span.get("messaging.destination.name"):
                continue
            edge = edge_from_span(span, self.repository.tenant_id, self.repository.environment)
            edge["source_document_ref"] = source.get("_source_document_id")
            edges[edge["id"]] = edge
        self.repository.save(list(edges.values()), cursor, self.worker_id)
        return {"spans_read": len(spans), "edges_written": len(edges), "cursor": cursor}
