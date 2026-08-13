"""Pure contracts and calculations for evidence-led pathway investigations.

This module deliberately has no storage or web-framework dependencies.  It describes
dependency exposure and candidates; it never makes a root-cause claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal

AnchorType = Literal[
    "kafka_cluster",
    "topic",
    "partition",
    "consumer_group",
    "connector",
    "connector_task",
    "pathway",
    "pathway_node",
    "pathway_edge",
    "producer",
    "consumer",
    "service",
    "job",
    "dataset",
    "data_product",
]
DataStatus = Literal[
    "complete",
    "partial",
    "stale",
    "history_unavailable",
    "history_truncated",
    "not_yet_observed",
    "known_active",
    "known_inactive",
]


@dataclass(frozen=True)
class InvestigationAnchor:
    anchor_type: AnchorType
    anchor_id: str

    def __post_init__(self) -> None:
        allowed = {
            "kafka_cluster",
            "topic",
            "partition",
            "consumer_group",
            "connector",
            "connector_task",
            "pathway",
            "pathway_node",
            "pathway_edge",
            "producer",
            "consumer",
            "service",
            "job",
            "dataset",
            "data_product",
        }
        if self.anchor_type not in allowed or not isinstance(self.anchor_id, str) or not self.anchor_id:
            raise ValueError("unsupported investigation anchor")


@dataclass(frozen=True)
class InvestigationWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("window end must be after start")


@dataclass(frozen=True)
class HistoricalNode:
    node_id: str
    node_type: str
    display_name: str = ""
    confidence: float = 1.0
    source_coverage: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    data_status: str = "complete"


@dataclass(frozen=True)
class HistoricalEdge:
    edge_id: str
    source_node_id: str
    destination_node_id: str
    relationship: str
    topic: str | None = None
    consumer_group: str | None = None
    confidence: float = 1.0
    source_coverage: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    data_status: str = "complete"


@dataclass(frozen=True)
class TopologySnapshot:
    snapshot_id: str
    tenant_id: str
    environment: str
    pathway_id: str
    effective_at: datetime
    observed_at: datetime
    graph_hash: str
    nodes: tuple[HistoricalNode, ...]
    edges: tuple[HistoricalEdge, ...]
    classification: str = "partial"
    confidence: float = 0.0
    source_coverage: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    change_reason_codes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    schema_version: str = "v1"


@dataclass(frozen=True)
class TraversalRequest:
    anchor: InvestigationAnchor
    direction: Literal["upstream", "downstream", "both"] = "downstream"
    max_hops: int = 5
    max_nodes: int = 100
    max_edges: int = 200
    max_paths: int = 100

    def __post_init__(self) -> None:
        limits = (
            ("max_hops", self.max_hops, 8),
            ("max_nodes", self.max_nodes, 500),
            ("max_edges", self.max_edges, 1000),
            ("max_paths", self.max_paths, 500),
        )
        for name, value, maximum in limits:
            if value < 1 or value > maximum:
                raise ValueError(f"{name} must be between 1 and {maximum}")


@dataclass(frozen=True)
class TraversalPath:
    entity_id: str
    distance: int
    relationship: str
    path: tuple[str, ...]
    confidence: float
    source_coverage: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    data_status: str


@dataclass(frozen=True)
class ImpactCandidate:
    entity_type: str
    entity_id: str
    display_name: str
    distance: int
    relationship: str
    path_ids: tuple[str, ...]
    classification: Literal["direct", "transitive", "associated", "inferred", "unknown"]
    confidence: float
    source_coverage: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    data_status: str = "complete"
    active_reliability_breach: bool | None = None
    active_anomaly: bool | None = None
    retention_risk: str | None = None
    failure_candidate: bool | None = None
    first_observed: datetime | None = None
    last_observed: datetime | None = None


@dataclass(frozen=True)
class BlastRadiusResult:
    anchor: InvestigationAnchor
    direction: str
    paths: tuple[TraversalPath, ...]
    candidates: tuple[ImpactCandidate, ...]
    truncated: bool = False
    truncation_reason: str | None = None
    excluded_node_count: int | None = None
    excluded_edge_count: int | None = None
    lineage_enrichment_status: str = "unavailable"


@dataclass(frozen=True)
class BottleneckCandidate:
    rank: int
    edge_id: str
    resource_id: str
    dimension: str
    observed_value: float
    pathway_total_or_baseline: float
    contribution_percentage: float
    confidence: float
    source_coverage: tuple[str, ...]
    calculation_method: str
    explanation: str = "Highest observed contribution; this is not a root-cause claim."
    anomaly_state: str = "no_data"
    reliability_state: str = "no_data"
    missing_inputs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class WindowMetric:
    name: str
    value: float | None
    sample_count: int
    coverage: float


@dataclass(frozen=True)
class WindowComparison:
    metric: str
    before_value: float | None
    after_value: float | None
    absolute_delta: float | None
    relative_delta: float | None
    relative_delta_available: bool
    reason_code: str | None
    before_sample_count: int
    after_sample_count: int
    before_coverage: float
    after_coverage: float
    sample_sufficient: bool
    confidence: float


@dataclass(frozen=True)
class TopologyDiff:
    nodes_added: tuple[str, ...] = ()
    nodes_removed: tuple[str, ...] = ()
    edges_added: tuple[str, ...] = ()
    edges_removed: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeOverlay:
    change_type: str
    change_at: datetime
    degradation_at: datetime | None
    delta_seconds: int | None
    evidence_ref: str


@dataclass(frozen=True)
class EvidenceTimelineItem:
    event_id: str
    event_type: str
    effective_at: datetime
    observed_at: datetime
    resource_type: str
    resource_id: str
    severity: str
    summary: str
    provenance: str
    confidence: float
    source: str
    evidence_ref: str


@dataclass(frozen=True)
class InvestigationCompleteness:
    data_status: str
    source_coverage: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationEvidence:
    evidence: tuple[EvidenceTimelineItem, ...] = ()
    related_entities: tuple[ImpactCandidate, ...] = ()
    provider_status: str = "partial"
    truncated: bool = False
    request_id: str = ""
    completeness: InvestigationCompleteness = field(default_factory=lambda: InvestigationCompleteness("partial"))


def canonical_graph_hash(
    nodes: list[HistoricalNode] | tuple[HistoricalNode, ...], edges: list[HistoricalEdge] | tuple[HistoricalEdge, ...]
) -> str:
    """Hash semantic identity only; health, metrics, confidence and time are excluded."""
    identity = {
        "nodes": sorted((n.node_id, n.node_type) for n in nodes),
        "edges": sorted(
            (e.edge_id, e.source_node_id, e.destination_node_id, e.relationship, e.topic, e.consumer_group)
            for e in edges
        ),
    }
    return hashlib.sha256(json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def compare_metric(before: WindowMetric, after: WindowMetric, *, minimum_samples: int = 1) -> WindowComparison:
    sufficient = before.sample_count >= minimum_samples and after.sample_count >= minimum_samples
    before_value, after_value = before.value, after.value
    absolute = None if before_value is None or after_value is None else after_value - before_value
    reason = "missing_value" if absolute is None else ("zero_baseline" if before.value == 0 else None)
    relative = None if absolute is None or before_value is None or before_value == 0 else absolute / abs(before_value)
    confidence = min(before.coverage, after.coverage) if sufficient else 0.0
    return WindowComparison(
        before.name,
        before.value,
        after.value,
        absolute,
        relative,
        relative is not None,
        reason,
        before.sample_count,
        after.sample_count,
        before.coverage,
        after.coverage,
        sufficient,
        round(confidence, 3),
    )


def snapshot_document(snapshot: TopologySnapshot) -> dict[str, object]:
    """Return a strict, bounded persistence document."""
    value = asdict(snapshot)
    value["node_ids"] = [n.node_id for n in snapshot.nodes]
    value["edge_ids"] = [e.edge_id for e in snapshot.edges]
    value["node_count"] = len(snapshot.nodes)
    value["edge_count"] = len(snapshot.edges)
    return value
