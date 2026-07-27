from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal

from pydantic import Field, field_validator

from .base import DomainModel, ProductEntity, utc_now


class DataProductCriticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataProductOwner(DomainModel):
    team: str
    support_url: str | None = None
    on_call_url: str | None = None


class DataProductOutput(DomainModel):
    entity_id: str
    entity_type: Literal["asset", "api", "kafka_topic", "dashboard", "model", "application", "app"]
    display_name: str = ""
    primary: bool = False
    evidence_refs: List[str] = Field(default_factory=list)
    lineage_evidence_refs: List[str] = Field(default_factory=list)  # legacy read compatibility
    observed_at: datetime = Field(default_factory=utc_now)


class DataProductMember(DomainModel):
    id: str = ""
    product_id: str = ""
    tenant_id: str = ""
    environment: str = "default"
    entity_id: str
    entity_type: str
    membership_source: Literal["manual", "lineage", "dependency", "import"]
    state: Literal["active", "excluded", "removed"] = "active"
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1, ge=0, le=1)
    excluded: bool = False
    observed_at: datetime = Field(default_factory=utc_now)


class DataProductMembershipEvidence(DomainModel):
    ref: str
    source: Literal["output", "lineage", "pathway", "dependency", "manual"]
    observed_at: datetime


class DataProductMembership(DomainModel):
    membership_id: str
    product_id: str
    tenant_id: str
    environment: str
    entity_id: str
    entity_type: str
    source: Literal["manual", "lineage", "dependency", "import", "proposal"]
    state: Literal["active", "excluded", "removed"] = "active"
    proposal_id: str | None = None
    evidence_refs: List[str] = Field(default_factory=list, max_length=50)
    confidence: float = Field(default=1, ge=0, le=1)
    source_coverage: float = Field(default=1, ge=0, le=1)
    observed_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str
    excluded_at: datetime | None = None
    excluded_by: str | None = None
    exclusion_reason: str | None = None
    revision: int = Field(default=1, ge=1)
    etag: str
    schema_version: str = "v1"


class DataProductMembershipPage(DomainModel):
    items: List[DataProductMembership]
    next_cursor: str | None = None
    has_more: bool = False
    search_after: List[str | int | float] | None = None


class DataProductMembershipProposal(DomainModel):
    proposal_id: str
    product_id: str
    tenant_id: str
    environment: str
    entity_id: str
    entity_type: str
    source: Literal["lineage", "dependency", "import"]
    state: Literal["proposed", "accepted", "rejected", "superseded", "expired"] = "proposed"
    evidence_refs: List[str] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0, le=1)
    source_coverage: float = Field(ge=0, le=1)
    missing_inputs: List[str] = Field(default_factory=list, max_length=50)
    truncated: bool = False
    observed_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    proposal_revision: int = Field(ge=1)
    schema_version: str = "v1"

    @property
    def id(self) -> str:  # compatibility for callers predating the typed projection
        return self.proposal_id


class DataProductMembershipProposalPage(DomainModel):
    items: List[DataProductMembershipProposal]
    next_cursor: str | None = None
    has_more: bool = False
    search_after: List[str | int | float] | None = None


class DataProductMembershipDecision(DomainModel):
    decision_id: str
    tenant_id: str
    environment: str
    product_id: str
    proposal_id: str | None = None
    membership_id: str | None = None
    decision: Literal["add", "accept", "reject", "expire", "supersede", "exclude"]
    operation_id: str | None = None
    outcome: Literal["pending", "applied", "superseded", "failed"] = "applied"
    actor: str
    reason: str
    idempotency_key_hash: str
    request_fingerprint: str
    expected_revision: int | None = None
    result_revision: int | None = None
    result_etag: str | None = None
    error_code: str | None = None
    decided_at: datetime = Field(default_factory=utc_now)
    occurred_at: datetime = Field(default_factory=utc_now)
    applied_at: datetime | None = None
    schema_version: str = "v1"


class DataProductMembershipDecisionPage(DomainModel):
    items: List[DataProductMembershipDecision]
    next_cursor: str | None = None
    has_more: bool = False
    search_after: List[str | int | float] | None = None


class DataProductMembershipGenerationResult(DomainModel):
    generated: int = Field(ge=0)
    existing: int = Field(ge=0)
    superseded: int = Field(ge=0)
    truncated: bool
    source_coverage: float = Field(ge=0, le=1)
    missing_inputs: List[str] = Field(default_factory=list, max_length=50)
    observed_at: datetime


class DataProductDependency(DomainModel):
    upstream_product_id: str
    evidence_refs: List[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=utc_now)


class DataProductDependencyProjection(DomainModel):
    tenant_id: str
    environment: str
    product_id: str
    upstream_product_id: str
    relationship: str = Field(default="depends_on", max_length=100)
    source: str = Field(default="declared", max_length=100)
    evidence_refs: List[str] = Field(default_factory=list, max_length=50)
    confidence: float = Field(default=1, ge=0, le=1)
    observed_at: datetime = Field(default_factory=utc_now)
    product_revision: int = Field(ge=1)
    graph_version: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    removed: bool = False
    removed_at: datetime | None = None
    removed_by_revision: int | None = Field(default=None, ge=1)
    schema_version: str = "v1"


class DataProductDependencyPage(DomainModel):
    items: List[DataProductDependencyProjection]
    has_more: bool = False
    search_after: List[str | int | float] | None = None
    next_cursor: str | None = None


class DataProductDependencyGraph(DomainModel):
    nodes: List[str]
    edges: List[DataProductDependencyProjection]
    direction: Literal["upstream", "downstream"]
    depth_reached: int = Field(ge=0)
    visited_count: int = Field(ge=0)
    truncated: bool = False
    cycle_detected: bool = False
    cycle_path: List[str] = Field(default_factory=list, max_length=100)
    missing_evidence: List[str] = Field(default_factory=list, max_length=50)
    graph_version: str
    observed_at: datetime = Field(default_factory=utc_now)


class DataProductImpactSummary(DomainModel):
    tenant_id: str
    environment: str
    product_id: str
    outputs: List[str] = Field(default_factory=list, max_length=500)
    active_members: List[str] = Field(default_factory=list, max_length=500)
    direct_upstream_products: List[str] = Field(default_factory=list, max_length=500)
    direct_downstream_products: List[str] = Field(default_factory=list, max_length=500)
    transitive_upstream_products: List[str] = Field(default_factory=list, max_length=1000)
    transitive_downstream_products: List[str] = Field(default_factory=list, max_length=1000)
    pathways: List[str] = Field(default_factory=list, max_length=500)
    known_consumers: List[str] = Field(default_factory=list, max_length=500)
    truncated: bool = False
    missing_evidence: List[str] = Field(default_factory=list, max_length=50)
    source_coverage: float = Field(default=0, ge=0, le=1)
    data_status: Literal["complete", "partial", "unavailable"] = "partial"
    observed_at: datetime = Field(default_factory=utc_now)


class DataProductSLODefinition(DomainModel):
    id: str
    product_id: str
    tenant_id: str
    environment: str
    component: Literal[
        "freshness",
        "quality",
        "availability",
        "pipeline_success",
        "pipeline_duration",
        "stream_lag",
        "throughput",
        "error_rate",
        "schema_stability",
    ]
    objective: float = Field(ge=0, le=1)
    window: str
    evaluation_method: str
    source_monitor_ids: List[str] = Field(default_factory=list)
    weight: float = Field(default=1, ge=0)
    critical: bool = False
    revision: int = Field(default=1, ge=1)
    etag: str
    state: Literal["draft", "active", "disabled", "archived"] = "draft"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DataProductSLOEvaluation(DomainModel):
    id: str
    tenant_id: str
    environment: str
    product_id: str
    slo_id: str
    definition_revision: int
    window_start: datetime
    window_end: datetime
    objective: float
    actual_value: float | None = None
    denominator: float = 0
    exclusions: List[str] = Field(default_factory=list)
    source_monitor_ids: List[str] = Field(default_factory=list)
    source_evaluation_refs: List[str] = Field(default_factory=list)
    coverage: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    missing_evidence: List[str] = Field(default_factory=list)
    state: Literal["passed", "failed", "unknown", "insufficient_data", "source_unavailable", "stale"]
    evaluated_at: datetime


class DataProductCoverage(DomainModel):
    state: Literal[
        "covered", "partially_covered", "not_covered", "not_applicable", "not_configured", "degraded", "unknown"
    ]
    value: float | None = Field(default=None, ge=0, le=1)
    missing_dimensions: List[str] = Field(default_factory=list)


class DataProductReliability(DomainModel):
    component_values: Dict[str, float | None]
    component_weights: Dict[str, float]
    missing_components: List[str] = Field(default_factory=list)
    stale_components: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    observed_period: str
    overall_score: float | None = Field(default=None, ge=0, le=100)
    overall_state: Literal["healthy", "at_risk", "unhealthy", "unknown"]
    trend: Literal["improving", "stable", "declining", "unknown"] = "unknown"
    formula: str = "weighted sum of observed, non-stale components / observed weights"


class DataProductIncidentSummary(DomainModel):
    open_incidents: int = Field(default=0, ge=0)
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    mtta_seconds: float | None = Field(default=None, ge=0)
    mttr_seconds: float | None = Field(default=None, ge=0)
    recurrence_count: int = Field(default=0, ge=0)
    latest_incident: str | None = None
    affected_entities: List[str] = Field(default_factory=list)


class DataProductChange(DomainModel):
    change_type: str
    occurred_at: datetime
    evidence_ref: str


class DataProductImpact(DomainModel):
    outputs: List[str] = Field(default_factory=list)
    members: List[str] = Field(default_factory=list)
    upstream_products: List[str] = Field(default_factory=list)
    downstream_products: List[str] = Field(default_factory=list)
    pathways: List[str] = Field(default_factory=list)
    known_consumers: List[str] = Field(default_factory=list)
    truncated: bool = False
    missing_evidence: List[str] = Field(default_factory=list)


class DataProductRevisionEvent(DomainModel):
    operation_id: str
    product_id: str
    tenant_id: str
    environment: str
    revision: int
    etag: str
    definition_checksum: str
    actor: str
    reason: str
    action: Literal["create", "update", "activate", "deprecate", "archive"] = "update"
    outcome: Literal["pending", "applied", "superseded", "failed"] = "pending"
    occurred_at: datetime = Field(default_factory=utc_now)
    applied_at: datetime | None = None
    error_code: str | None = None


class DataProductOperationResult(DomainModel):
    """Immutable operation outcome and the exact snapshot returned on replay."""

    operation_id: str
    action: Literal["create", "update", "activate", "deprecate", "archive"]
    outcome: Literal["applied", "superseded", "failed"]
    product: DataProductDefinition
    revision: int = Field(ge=1)
    etag: str
    definition_checksum: str
    actor: str
    reason: str
    occurred_at: datetime
    applied_at: datetime | None = None


class RepositoryPageMetadata(DomainModel):
    has_more: bool = False
    search_after: List[str | int | float] | None = None


class DataProductOperationPage(DomainModel):
    items: List[DataProductRevisionEvent]
    metadata: RepositoryPageMetadata = Field(default_factory=RepositoryPageMetadata)


class DataProductRevisionPage(DataProductOperationPage):
    pass


class DataProductDefinition(ProductEntity):
    revision: int = Field(default=1, ge=1)
    etag: str
    name: str
    description: str = ""
    domain: str
    criticality: DataProductCriticality
    lifecycle_state: Literal["draft", "active", "deprecated", "archived"] = "draft"
    owner: DataProductOwner
    tags: List[str] = Field(default_factory=list)
    outputs: List[DataProductOutput] = Field(default_factory=list)
    members: List[DataProductMember] = Field(default_factory=list)  # compatibility only; repository stores separately
    dependencies: List[DataProductDependency] = Field(default_factory=list)
    slos: List[DataProductSLODefinition] = Field(default_factory=list)

    @field_validator("outputs")
    @classmethod
    def unique_outputs(cls, outputs: List[DataProductOutput]) -> List[DataProductOutput]:
        keys = [(item.entity_type, item.entity_id) for item in outputs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate data product output")
        return outputs


DataProduct = DataProductDefinition
DataProductSLO = DataProductSLODefinition
DataProductBusinessImpact = DataProductImpact
