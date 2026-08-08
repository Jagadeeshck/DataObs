from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class LifecycleState(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class EnforcementMode(str, Enum):
    OBSERVE = "observe"
    WARN = "warn"
    ENFORCE = "enforce"
    DISABLED = "disabled"


class CompatibilityMode(str, Enum):
    STRICT = "strict"
    BACKWARD = "backward"
    FORWARD = "forward"
    FULL = "full"
    CUSTOM_BOUNDED = "custom_bounded"


@dataclass(frozen=True)
class ColumnRule:
    name: str
    required: bool = False
    expected_type: str | None = None
    compatible_types: tuple[str, ...] = ()
    nullable: bool | None = None
    description: str | None = None
    semantic_type: str | None = None
    classification: str | None = None
    constraints: tuple[str, ...] = ()
    ordinal: int | None = None


@dataclass(frozen=True)
class QualityRequirement:
    monitor_id: str
    required_state: str = "healthy"
    severity: str = "medium"
    evidence_max_age_seconds: int | None = None


@dataclass(frozen=True)
class ContractVersion:
    contract_id: str
    version: int
    revision_id: str
    lifecycle_state: LifecycleState
    effective_from: datetime | None
    effective_until: datetime | None
    columns: tuple[ColumnRule, ...] = ()
    quality_requirements: tuple[QualityRequirement, ...] = ()
    freshness_max_age_seconds: int | None = None
    freshness_grace_seconds: int = 0
    volume_min: int | None = None
    volume_max: int | None = None
    compatibility: CompatibilityMode = CompatibilityMode.STRICT
    metadata_requirements: tuple[str, ...] = ()
    rationale: str = ""
    change_summary: str = ""
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approval_evidence: dict[str, Any] | None = None

    @property
    def fingerprint(self) -> str:
        payload = asdict(self)
        payload.pop("approval_evidence", None)
        payload["lifecycle_state"] = self.lifecycle_state.value
        payload["compatibility"] = self.compatibility.value
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass
class DataContract:
    contract_id: str
    tenant_id: str
    environment: str
    asset_id: str
    canonical_asset_identity: str
    name: str
    description: str
    owner: str
    owner_team: str
    producer_owners: tuple[str, ...] = ()
    consumer_owners: tuple[str, ...] = ()
    data_product_ids: tuple[str, ...] = ()
    criticality: str = "medium"
    lifecycle_state: LifecycleState = LifecycleState.DRAFT
    enforcement_mode: EnforcementMode = EnforcementMode.OBSERVE
    current_version: int = 1
    effective_version: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    updated_by: str = ""
    revision: int = 1
    tags: tuple[str, ...] = ()
    evidence_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    @property
    def etag(self) -> str:
        return f'W/"{self.revision}"'


@dataclass(frozen=True)
class Evidence:
    observed_at: datetime
    schema_columns: tuple[dict[str, Any], ...] | None = None
    monitor_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    freshness_age_seconds: float | None = None
    record_count: int | None = None
    asset_metadata: dict[str, Any] = field(default_factory=dict)
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class Violation:
    violation_id: str
    requirement_id: str
    category: str
    field: str | None
    expected: Any
    observed: Any
    severity: str
    directness: str
    reason_code: str


@dataclass(frozen=True)
class ContractEvaluation:
    evaluation_id: str
    contract_id: str
    contract_version: int
    asset_id: str
    evaluated_at: datetime
    observation_time: datetime
    overall_state: str
    enforcement_mode: str
    score: float | None
    confidence: float
    components: dict[str, float | None]
    formula: str
    violations: tuple[Violation, ...]
    unavailable_requirements: tuple[str, ...]
    stale_requirements: tuple[str, ...]
    evidence_references: tuple[str, ...]
    effective_contract_fingerprint: str
    reason_codes: tuple[str, ...]
    schema_version: int = 1
