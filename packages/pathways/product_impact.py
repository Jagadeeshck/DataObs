"""Pure stream/pathway to Data Product impact semantics.

This module deliberately contains no persistence or web framework imports.  A
downstream relationship is exposure evidence, never proof of impact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class BindingMethod(str, Enum):
    DECLARED = "declared"
    REVIEWED_MEMBERSHIP = "reviewed_membership"
    DECLARED_OUTPUT = "declared_output"
    LINEAGE_SUPPORTED = "lineage_supported"
    PATHWAY_SUPPORTED = "pathway_supported"
    APPLICATION_SUPPORTED = "application_supported"
    STRONGLY_CORRELATED = "strongly_correlated"
    WEAKLY_CORRELATED = "weakly_correlated"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class ExposureState(str, Enum):
    LINKED = "linked"
    POTENTIALLY_EXPOSED = "potentially_exposed"
    OBSERVED_DEGRADATION = "observed_degradation"
    SLO_IMPACT_OBSERVED = "slo_impact_observed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class CanonicalMessagingResource(Model):
    messaging_system: str
    resource_kind: str
    canonical_resource_id: str
    provider_resource_id: str | None = None


class ProductBindingEvidence(Model):
    ref: str
    source: str
    observed_at: datetime
    confidence: float = Field(ge=0, le=1)


class StreamProductBinding(Model):
    binding_id: str
    tenant_id: str
    environment: str
    resource_id: str
    resource_type: str
    messaging_system: str
    product_id: str
    relationship: Literal[
        "product_output",
        "product_member",
        "product_input",
        "product_dependency",
        "pathway_member",
        "producer_for",
        "consumer_of",
        "feeds",
        "derived_from",
        "serves",
        "associated",
        "inferred",
    ]
    binding_method: BindingMethod
    confidence: float = Field(ge=0, le=1)
    source_coverage: float = Field(ge=0, le=1)
    observed_at: datetime
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    missing_inputs: list[str] = Field(default_factory=list, max_length=50)
    data_status: Literal["complete", "partial", "unavailable"] = "complete"


class ProductCriticalityContext(Model):
    criticality: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    source: str | None = None
    observed_at: datetime | None = None


class ProductOwnerContext(Model):
    owner_team: str | None = None
    support_url: str | None = None
    on_call_url: str | None = None
    source: str | None = None
    source_revision: str | None = None
    observed_at: datetime | None = None


class ProductSLOContext(Model):
    overall_reliability_state: str = "unknown"
    overall_reliability_score: float | None = Field(default=None, ge=0, le=100)
    failed_slo_count: int = Field(default=0, ge=0)
    at_risk_slo_count: int = Field(default=0, ge=0)
    unknown_slo_count: int = Field(default=0, ge=0)
    stream_related_slos: list[str] = Field(default_factory=list, max_length=50)
    related_failure_observed: bool = False
    observed_at: datetime | None = None


class ProductConsumerContext(Model):
    consumer_id: str
    consumer_type: Literal["application", "service", "job", "dashboard", "api", "data_product"]
    classification: Literal["declared", "observed", "lineage_supported", "pathway_supported", "inferred", "unknown"]
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)


class ProductExposurePath(Model):
    nodes: list[str] = Field(max_length=100)
    edge_evidence_refs: list[list[str]] = Field(default_factory=list, max_length=100)


class ProductExposure(Model):
    product_id: str
    relationship: str
    classification: Literal["direct", "transitive", "associated"]
    distance: int = Field(ge=0, le=8)
    exposure_state: ExposureState
    exposure_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    criticality: ProductCriticalityContext = Field(default_factory=ProductCriticalityContext)
    owner: ProductOwnerContext = Field(default_factory=ProductOwnerContext)
    slo: ProductSLOContext = Field(default_factory=ProductSLOContext)
    paths: list[ProductExposurePath] = Field(default_factory=list, max_length=20)
    known_consumers: list[ProductConsumerContext] = Field(default_factory=list, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    missing_inputs: list[str] = Field(default_factory=list, max_length=50)
    observed_at: datetime


class ImpactEvidenceSummary(Model):
    linked: int = 0
    potentially_exposed: int = 0
    observed_degradation: int = 0
    slo_impact_observed: int = 0
    critical_products: int = 0


class ImpactCompleteness(Model):
    product_context_status: Literal["complete", "partial", "unavailable", "permission_denied"]
    missing_inputs: list[str] = Field(default_factory=list, max_length=50)
    truncated: bool = False
    cycle_detected: bool = False
    depth_reached: int = Field(default=0, ge=0, le=8)


class StreamProductImpact(Model):
    tenant_id: str
    environment: str
    resource_id: str
    products: list[ProductExposure] = Field(default_factory=list, max_length=200)
    summary: ImpactEvidenceSummary = Field(default_factory=ImpactEvidenceSummary)
    completeness: ImpactCompleteness
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PathwayProductImpact(StreamProductImpact):
    pathway_id: str


def impact_identity(tenant: str, environment: str, anchor_type: str, anchor_id: str, product_id: str) -> str:
    """Stable identity excludes mutable exposure state."""
    return sha256("\0".join((tenant, environment, anchor_type, anchor_id, product_id)).encode()).hexdigest()


def evaluate_exposure(
    *, stream_degraded: bool, product_degraded: bool = False, related_slo_failed: bool = False, recovering: bool = False
) -> ExposureState:
    if recovering:
        return ExposureState.RECOVERING
    if stream_degraded and related_slo_failed:
        return ExposureState.SLO_IMPACT_OBSERVED
    if stream_degraded and product_degraded:
        return ExposureState.OBSERVED_DEGRADATION
    if stream_degraded:
        return ExposureState.POTENTIALLY_EXPOSED
    return ExposureState.LINKED


def exposure_score(
    *,
    criticality: str | None,
    relationship_strength: float | None,
    distance: int | None,
    stream_severity: float | None,
    slo_evidence: float | None,
    source_coverage: float | None,
) -> float | None:
    """Weighted available evidence; absent components are renormalized."""
    criticality_values = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
    values = [
        (25, criticality_values.get(criticality or "")),
        (20, relationship_strength),
        (10, None if distance is None else max(0.0, 1 - min(distance, 8) / 8)),
        (15, stream_severity),
        (20, slo_evidence),
        (10, source_coverage),
    ]
    available = [(weight, min(1.0, max(0.0, value))) for weight, value in values if value is not None]
    return None if not available else round(100 * sum(w * v for w, v in available) / sum(w for w, _ in available), 2)


def exposure_confidence(
    *,
    binding_strength: float,
    source_coverage: float,
    topology_completeness: float | None = None,
    freshness: float | None = None,
    slo_coverage: float | None = None,
    lineage_availability: float | None = None,
) -> float:
    values = [binding_strength, source_coverage, topology_completeness, freshness, slo_coverage, lineage_availability]
    available = [min(1.0, max(0.0, v)) for v in values if v is not None]
    return round(sum(available) / len(available), 4) if available else 0.0
