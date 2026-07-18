"""Public product-query contracts for pathway and asset investigation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    stale = "stale"
    not_configured = "not_configured"
    unknown = "unknown"
    unavailable = "unavailable"


class ProductResponse(BaseModel):
    data_status: DataStatus = DataStatus.unknown
    observed_at: datetime | None = None
    source_coverage: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None
    trace_id: str | None = None


class PathwayEvidence(BaseModel):
    evidence_type: Literal[
        "trace_observed",
        "openlineage_observed",
        "kafka_metric_observed",
        "catalog_declared",
        "structural",
        "inferred",
        "unknown",
    ]
    confidence: float = Field(ge=0, le=1)
    observed_at: datetime | None = None
    source_document_reference: str | None = None
    source_integration: str | None = None
    coverage: Literal["complete", "partial"] = "partial"
    active: bool = True


class PathwayRouteNode(BaseModel):
    id: str
    name: str
    node_type: str


class PathwayRouteEdge(BaseModel):
    id: str
    source_node_id: str
    destination_node_id: str
    evidence: PathwayEvidence
    health: str = "unknown"


class PathwayRoute(BaseModel):
    id: str
    nodes: list[PathwayRouteNode] = Field(default_factory=list)
    edges: list[PathwayRouteEdge] = Field(default_factory=list)
    complete: bool = False
    confidence: float = Field(ge=0, le=1)
    rank_score: float = 0
    ranking_explanation: dict[str, float] = Field(default_factory=dict)


class PathwaySearchRequest(BaseModel):
    start_node_id: str = Field(min_length=1, max_length=512)
    end_node_id: str | None = Field(default=None, max_length=512)
    direction: Literal["upstream", "downstream"] = "downstream"
    max_hops: int = Field(default=6, ge=1, le=12)
    max_paths: int = Field(default=10, ge=1, le=20)
    minimum_confidence: float = Field(default=0, ge=0, le=1)
    include_partial: bool = True
    active_only: bool = True


class PathwaySearchResponse(ProductResponse):
    best_path: PathwayRoute | None = None
    alternative_paths: list[PathwayRoute] = Field(default_factory=list)
    partial_paths: list[PathwayRoute] = Field(default_factory=list)
    excluded_path_count: int = 0
    truncated: bool = False


# Backwards-compatible name retained for clients generated from PR #91.
PathwaySearchResult = PathwaySearchResponse


class PathwayMetricSummary(ProductResponse):
    throughput_messages_per_second: float | None = None
    throughput_bytes_per_second: float | None = None
    lag_messages: int | None = None
    lag_seconds: float | None = None
    error_rate: float | None = None
    retry_rate: float | None = None
    dlq_rate: float | None = None
    retention_risk: str | None = None
    sample_count: int | None = None
    last_seen: datetime | None = None


class PathwayLatencySummary(ProductResponse):
    method: Literal["trace_derived", "edge_estimate", "unavailable"] = "unavailable"
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None
    sample_count: int | None = None
    missing_segments: list[str] = Field(default_factory=list)


class PathwayBottleneck(ProductResponse):
    edge_id: str
    view: Literal["latency", "reliability", "backlog", "retention_risk"]
    contribution_percentage: float | None = None
    absolute_contribution: float | None = None
    calculation_method: str
    missing_inputs: list[str] = Field(default_factory=list)
    health_explanation: str | None = None


class PathwayWindowComparison(ProductResponse):
    metric_deltas: dict[str, float | None] = Field(default_factory=dict)
    new_edges: list[str] = Field(default_factory=list)
    removed_edges: list[str] = Field(default_factory=list)
    sample_sufficient: bool = False
    suspected_correlated_changes: list[str] = Field(default_factory=list)


PathwayComparison = PathwayWindowComparison


class PathwayImpactSummary(ProductResponse):
    affected_asset_ids: list[str] = Field(default_factory=list)
    active_incident_ids: list[str] = Field(default_factory=list)
    truncated: bool = False


PathwayImpact = PathwayImpactSummary


class PathwayMonitor(BaseModel):
    id: str
    tenant_id: str
    environment: str
    pathway_id: str
    monitor_type: str
    threshold: float | None = None
    evaluation_window_seconds: int = Field(ge=60, le=86400)
    enabled: bool = True
    revision: int = 1
    owner_team: str | None = None
    business_service: str | None = None


class PathwayMonitorResult(ProductResponse):
    monitor_id: str
    state: str
    measured_value: float | None = None


class AssetSummary(ProductResponse):
    id: str
    name: str
    fqn: str | None = None
    asset_type: str
    health: str = "unknown"
    owner_team: str | None = None
    business_service: str | None = None
    environment: str
    source: str | None = None


class AssetMetadata(ProductResponse):
    asset: AssetSummary
    tags: list[str] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=list)


class AssetHealthReason(BaseModel):
    signal: str
    severity: str
    explanation: str
    observed_at: datetime | None = None


class AssetHealth(ProductResponse):
    state: Literal["healthy", "degraded", "warning", "critical", "unknown", "not_configured"]
    reasons: list[AssetHealthReason] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class AssetSchemaSummary(ProductResponse):
    columns: list[dict[str, Any]] = Field(default_factory=list)
    schema_fingerprint: str | None = None
    changes: list[dict[str, Any]] = Field(default_factory=list)


class AssetFreshnessSummary(ProductResponse):
    latest_source_timestamp: datetime | None = None
    age_seconds: float | None = None
    sla_seconds: float | None = None
    calculation_strategy: str | None = None


class AssetQualitySummary(ProductResponse):
    checks: list[dict[str, Any]] = Field(default_factory=list)


class AssetUsageSummary(ProductResponse):
    access_count: int | None = None
    unique_consumers: int | None = None
    top_consumers: list[dict[str, Any]] = Field(default_factory=list)
    last_used: datetime | None = None


class AssetLineageSummary(ProductResponse):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[PathwayRouteEdge] = Field(default_factory=list)
    truncated: bool = False


class AssetIncidentSummary(ProductResponse):
    incidents: list[dict[str, Any]] = Field(default_factory=list)


class AssetChangeSummary(ProductResponse):
    changes: list[dict[str, Any]] = Field(default_factory=list)


class AssetSLO(ProductResponse):
    id: str
    name: str
    state: str


class AssetCostSummary(ProductResponse):
    compute_cost: float | None = None
    storage_cost: float | None = None
    network_cost: float | None = None
    allocation_method: str | None = None


class AssetAnnotation(BaseModel):
    id: str
    asset_id: str
    text: str = Field(min_length=1, max_length=4000)
    author: str
    revision: int = 1
    created_at: datetime
    updated_at: datetime
