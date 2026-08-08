from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GateStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error"
    CANCELLED = "cancelled"


class GateMode(StrEnum):
    ADVISORY = "advisory"
    ENFORCED = "enforced"
    DISABLED = "disabled"


@dataclass(frozen=True)
class PullRequestContext:
    provider: str
    repository: str
    pull_request_id: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str
    is_draft: bool = False
    author_subject: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class DriftThreshold:
    warning: float
    fail: float

    def __post_init__(self) -> None:
        if not 0 <= self.warning <= self.fail <= 1:
            raise ValueError("drift thresholds must satisfy 0 <= warning <= fail <= 1")


@dataclass(frozen=True)
class ChangeGatePolicy:
    policy_id: str = "default"
    version: int = 1
    enabled: bool = True
    project_id: str = "default"
    repository: str = "local"
    run_on_draft: bool = False
    checks_enabled: tuple[str, ...] = (
        "schema_change",
        "contract_compatibility",
        "impact_lineage",
        "data_drift",
        "dbt_tests",
    )
    max_lineage_depth: int = 5
    required_evidence: tuple[str, ...] = ()
    gate_mode: GateMode = GateMode.ENFORCED
    drift_thresholds: dict[str, DriftThreshold] = field(
        default_factory=lambda: {
            "row_count": DriftThreshold(0.10, 0.30),
            "null_rate": DriftThreshold(0.05, 0.15),
            "cardinality": DriftThreshold(0.15, 0.40),
            "numerical_distribution": DriftThreshold(0.10, 0.25),
            "categorical_distribution": DriftThreshold(0.10, 0.25),
        }
    )

    def fingerprint(self) -> str:
        return sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class CheckResult:
    check_id: str
    check_type: str
    status: str
    severity: str
    confidence: float
    summary: str
    reason_codes: list[str] = field(default_factory=list)
    changed_entities: list[dict[str, Any]] = field(default_factory=list)
    affected_entities: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence_status: str = "available"
    evidence_refs: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    completed_at: str = field(default_factory=utc_now)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
