from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal

from pydantic import Field

from .base import DomainModel, ProductEntity


class DataProductCriticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataProductOutput(DomainModel):
    entity_id: str
    entity_type: Literal["asset", "api", "kafka_topic", "dashboard", "model", "app"]
    lineage_evidence_refs: List[str] = Field(default_factory=list)


class DataProductMember(DomainModel):
    entity_id: str
    entity_type: str
    membership_source: Literal["manual", "lineage"]
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    excluded: bool = False


class DataProductDependency(DomainModel):
    upstream_product_id: str
    evidence_refs: List[str] = Field(default_factory=list)


class DataProductOwner(DomainModel):
    team: str
    support_url: str | None = None
    on_call_url: str | None = None


class DataProductSLO(DomainModel):
    id: str
    component: str
    objective: float
    window: str


class DataProductCoverage(DomainModel):
    state: str
    value: float | None = None
    missing_dimensions: List[str] = Field(default_factory=list)


class DataProductReliability(DomainModel):
    component_values: Dict[str, float | None]
    component_weights: Dict[str, float]
    missing_components: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    observed_period: str
    overall_score: float | None = None
    overall_state: Literal["healthy", "at_risk", "unhealthy", "unknown"]
    trend: Literal["improving", "stable", "declining", "unknown"] = "unknown"
    formula: str = "weighted sum of observed components / observed weights"


class DataProductIncidentSummary(DomainModel):
    open_incidents: int = 0
    mtta_seconds: float | None = None
    mttr_seconds: float | None = None
    recurrence_count: int = 0


class DataProductBusinessImpact(DomainModel):
    affected_consumers: int | None = None
    description: str | None = None


class DataProductCostCoverage(DomainModel):
    covered: bool = False
    monthly_cost: float | None = None
    currency: str | None = None


class DataProductChange(DomainModel):
    change_type: str
    occurred_at: datetime
    evidence_ref: str


class DataProduct(ProductEntity):
    name: str
    domain: str
    criticality: DataProductCriticality
    lifecycle_state: Literal["draft", "active", "deprecated", "archived"] = "draft"
    owner: DataProductOwner
    outputs: List[DataProductOutput] = Field(default_factory=list)
    members: List[DataProductMember] = Field(default_factory=list)
    dependencies: List[DataProductDependency] = Field(default_factory=list)
    slos: List[DataProductSLO] = Field(default_factory=list)
    etag: str
