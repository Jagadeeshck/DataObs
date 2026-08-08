"""Forward-only pathway topology history materializer."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Protocol

from packages.pathways.investigation import HistoricalEdge, HistoricalNode, TopologySnapshot, canonical_graph_hash


class HistoryStore(Protocol):
    def latest_snapshot(self, pathway_id: str) -> TopologySnapshot | None: ...
    def persist_snapshot(self, snapshot: TopologySnapshot, fencing_token: int) -> None: ...


class HistoryProjector:
    """Writes only material changes or bounded periodic safety snapshots."""

    def __init__(
        self, store: HistoryStore, tenant_id: str, environment: str, *, safety_interval: timedelta = timedelta(days=1)
    ):
        self.store, self.tenant_id, self.environment = store, tenant_id, environment
        self.safety_interval = safety_interval

    def materialize(
        self,
        pathway_id: str,
        nodes: list[HistoricalNode],
        edges: list[HistoricalEdge],
        *,
        effective_at: datetime,
        fencing_token: int,
        classification: str = "complete",
    ) -> TopologySnapshot | None:
        if len(nodes) > 500 or len(edges) > 1000:
            raise ValueError("topology exceeds snapshot safety limits")
        now = datetime.now(timezone.utc)
        graph_hash = canonical_graph_hash(nodes, edges)
        previous = self.store.latest_snapshot(pathway_id)
        safety_due = previous is not None and now - previous.observed_at >= self.safety_interval
        if previous and previous.graph_hash == graph_hash and not safety_due:
            return None
        reason = (
            "periodic_safety"
            if previous and previous.graph_hash == graph_hash
            else ("first_observation" if previous is None else "topology_changed")
        )
        snapshot = TopologySnapshot(
            str(uuid.uuid4()),
            self.tenant_id,
            self.environment,
            pathway_id,
            effective_at,
            now,
            graph_hash,
            tuple(sorted(nodes, key=lambda n: n.node_id)),
            tuple(sorted(edges, key=lambda e: e.edge_id)),
            classification,
            min([n.confidence for n in nodes] + [e.confidence for e in edges], default=0.0),
            tuple(sorted({source for item in [*nodes, *edges] for source in item.source_coverage})),
            () if classification == "complete" else ("complete_topology",),
            (reason,),
            tuple(sorted({ref for item in [*nodes, *edges] for ref in item.evidence_refs})),
        )
        self.store.persist_snapshot(snapshot, fencing_token)
        return snapshot
