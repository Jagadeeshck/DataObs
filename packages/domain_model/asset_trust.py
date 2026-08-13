"""Canonical, explainable asset trust contracts (not a guarantee of correctness)."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import DomainModel, utc_now

DIMENSIONS = (
    "quality",
    "freshness",
    "delivery_reliability",
    "slo_reliability",
    "contract_compliance",
    "schema_stability",
    "observability_coverage",
    "lineage_and_governance",
)
DEFAULT_WEIGHTS = dict(zip(DIMENSIONS, (0.20, 0.15, 0.15, 0.20, 0.10, 0.05, 0.10, 0.05)))


class AssetTrustEvidence(DomainModel):
    evidence_source: str
    evidence_ref: str
    dimension: str
    score: float | None = Field(default=None, ge=0, le=100)
    confidence: float = Field(default=1, ge=0, le=1)
    coverage: float = Field(default=1, ge=0, le=1)
    observed_at: datetime
    status: Literal["observed", "stale", "unknown", "not_configured"] = "observed"
    derived_from: list[str] = Field(default_factory=list)
    severity: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class AssetTrustDimension(DomainModel):
    name: str
    score: float | None = Field(default=None, ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_score: float | None = None
    status: str
    confidence: float = Field(ge=0, le=1)
    coverage: float = Field(ge=0, le=1)
    evidence_status: str
    evidence_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None


class CriticalCap(DomainModel):
    reason_code: str
    maximum_score: float = Field(ge=0, le=100)
    minimum_evidence_confidence: float = Field(default=0.8, ge=0, le=1)


class AssetTrustPolicy(DomainModel):
    policy_id: str
    name: str
    version: int = Field(default=1, ge=1)
    enabled: bool = True
    asset_types: list[str] = Field(default_factory=lambda: ["dataset", "table", "view", "dbt_model"])
    criticality_classes: list[str] = Field(default_factory=list)
    dimension_weights: dict[str, float] = Field(default_factory=lambda: DEFAULT_WEIGHTS.copy())
    required_dimensions: list[str] = Field(default_factory=lambda: ["quality", "freshness"])
    minimum_confidence: float = Field(default=0.6, ge=0, le=1)
    staleness_thresholds: dict[str, int] = Field(default_factory=dict)
    critical_caps: list[CriticalCap] = Field(
        default_factory=lambda: [
            CriticalCap(reason_code="contract.critical_violation", maximum_score=60),
            CriticalCap(reason_code="slo.budget_exhausted", maximum_score=65),
            CriticalCap(reason_code="freshness.critical_breach", maximum_score=50),
        ]
    )
    fallback_rules: dict[str, str] = Field(default_factory=dict)
    state_thresholds: dict[str, float] = Field(
        default_factory=lambda: {"strong": 90, "healthy": 80, "attention": 65, "poor": 40}
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    revision: int = Field(default=1, ge=1)
    etag: str = ""

    @model_validator(mode="after")
    def validate_policy(self):
        unknown = set(self.dimension_weights) - set(DIMENSIONS)
        if unknown:
            raise ValueError(f"unknown dimensions: {sorted(unknown)}")
        if set(self.required_dimensions) - set(DIMENSIONS):
            raise ValueError("required_dimensions contains an unknown dimension")
        if abs(sum(self.dimension_weights.values()) - 1) > 1e-9:
            raise ValueError("dimension weights must sum to one")
        return self


class AssetTrustScore(DomainModel):
    score_id: str
    tenant_id: str
    environment: str
    asset_id: str
    score: float | None = Field(default=None, ge=0, le=100)
    state: Literal["strong", "healthy", "attention", "poor", "critical", "unknown", "partial"]
    confidence: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    dimensions: list[AssetTrustDimension]
    missing_dimensions: list[str]
    stale_dimensions: list[str]
    reason_codes: list[str]
    top_positive_factors: list[str]
    top_negative_factors: list[str]
    evidence_refs: list[str]
    calculation_version: str = "asset-trust-v1"
    policy_id: str
    policy_version: int
    window_start: datetime
    window_end: datetime
    observed_at: datetime
    calculated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = "v1"
    formula: str
    available_weight: float = Field(ge=0, le=1)
    uncapped_score: float | None = Field(default=None, ge=0, le=100)
    cap_applied: bool = False
    cap_reason: str | None = None
    evidence_fingerprint: str


def score_identity(
    tenant_id: str,
    environment: str,
    asset_id: str,
    window_start: datetime,
    window_end: datetime,
    policy_id: str,
    policy_version: int,
    evidence_fingerprint: str,
    calculation_version: str = "asset-trust-v1",
) -> str:
    material = "\0".join(
        map(
            str,
            (
                tenant_id,
                environment,
                asset_id,
                window_start.isoformat(),
                window_end.isoformat(),
                policy_id,
                policy_version,
                evidence_fingerprint,
                calculation_version,
            ),
        )
    )
    return sha256(material.encode()).hexdigest()
