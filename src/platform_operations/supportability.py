"""Bounded, evidence-derived supportability views for the existing operations API."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from scripts.release.current_terminal_migration import migration_report

ROOT = Path(__file__).resolve().parents[2]


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNVALIDATED = "unvalidated"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class DiagnosticState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"
    UNVALIDATED = "unvalidated"


class MaintenanceState(StrEnum):
    NORMAL = "normal"
    PLANNED = "planned"
    ACTIVE = "active"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SupportProfile:
    state: SupportStatus
    evidence_source: str | None
    evidence_timestamp: str | None
    reason_code: str
    remediation_code: str


@dataclass(frozen=True)
class DiagnosticCheck:
    id: str
    state: DiagnosticState
    severity: str
    reason_code: str
    remediation_code: str
    checked_at: str


@dataclass(frozen=True)
class DiagnosticResult:
    state: DiagnosticState
    checks: tuple[DiagnosticCheck, ...]


@dataclass(frozen=True)
class ConfigurationFingerprint:
    schema_version: str
    fingerprint: str
    drift_state: str
    changed_categories: tuple[str, ...]


@dataclass(frozen=True)
class KnownIssue:
    issue_id: str
    title: str
    affected_versions: str
    affected_component: str
    severity: str
    state: str
    symptom_reason_codes: tuple[str, ...]
    workaround_reference: str | None
    fixed_version: str | None
    owner_team: str


@dataclass(frozen=True)
class EscalationTarget:
    reason_code: str
    primary_owner: str
    secondary_owner: str | None
    escalation_condition: str


@dataclass(frozen=True)
class OperationalReadiness:
    state: str
    categories: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class RunbookCoverage:
    covered: tuple[str, ...]
    missing: tuple[str, ...]


def _yaml(path: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / path).read_text())


def identities() -> dict[str, str]:
    chart = _yaml("helm/dataobs/Chart.yaml")
    candidate = _yaml("docs/release/first-supported-platform-candidate.yaml")
    return {
        "dataobs_version": str(chart["appVersion"]),
        "release_sha": str(candidate.get("candidate_source_sha") or "unknown"),
        "terminal_migration": migration_report()["terminal_migration"],
        "release_decision": "NO_GO",
    }


def support_view() -> dict[str, Any]:
    profile = _yaml("docs/operations/platform-support-profile.yaml")
    dimensions = profile["dimensions"]
    blockers = sorted(name for name, item in dimensions.items() if item["state"] in {"blocked", "unsupported"})
    return {
        **identities(),
        "support_profile": profile["overall_state"],
        "kubernetes_support_state": dimensions["kubernetes"]["state"],
        "elasticsearch_support_state": dimensions["elasticsearch"]["state"],
        "oidc_support_state": dimensions["oidc"]["state"],
        "ha_profile": dimensions["ha"]["state"],
        "capacity_profile": dimensions["scale"]["state"],
        "evidence_freshness": profile["evidence_freshness"],
        "known_blockers": blockers[:20],
    }


def diagnostic_view() -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    definitions = (
        ("application_identity", "healthy", "SEV4", "APPLICATION_IDENTITY_AVAILABLE", "NONE"),
        ("release_identity", "degraded", "SEV2", "RELEASE_VERIFICATION_FAILURE", "VERIFY_RELEASE_EVIDENCE"),
        ("migration_state", "unvalidated", "SEV2", "MIGRATION_EVIDENCE_UNAVAILABLE", "RUN_MIGRATION_DOCTOR"),
        (
            "elasticsearch_connectivity",
            "unknown",
            "SEV2",
            "ELASTICSEARCH_EVIDENCE_UNAVAILABLE",
            "CHECK_PLATFORM_HEALTH",
        ),
        ("oidc_configuration", "unvalidated", "SEV1", "OIDC_EVIDENCE_UNAVAILABLE", "VALIDATE_OIDC_CONFIGURATION"),
        ("worker_freshness", "unknown", "SEV2", "WORKER_EVIDENCE_UNAVAILABLE", "INSPECT_WORKER_STATUS"),
        ("backup_freshness", "unknown", "SEV2", "BACKUP_EVIDENCE_UNAVAILABLE", "VERIFY_BACKUP_EVIDENCE"),
        ("kubernetes_evidence", "unvalidated", "SEV1", "KUBERNETES_EVIDENCE_UNAVAILABLE", "RUN_KUBERNETES_VALIDATION"),
        ("telemetry_exporter", "unknown", "SEV3", "TELEMETRY_EVIDENCE_UNAVAILABLE", "INSPECT_TELEMETRY_STATUS"),
    )
    checks = [
        {
            "id": i,
            "state": state,
            "severity": severity,
            "reason_code": reason,
            "remediation_code": remediation,
            "checked_at": now,
        }
        for i, state, severity, reason, remediation in definitions
    ]
    return {"state": "degraded", "checks": checks}


def configuration_view(safe_configuration: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "store_backend": safe_configuration.get("store_backend", "unknown"),
        "auth_provider": safe_configuration.get("auth_provider", "unknown"),
        "oidc_enabled": bool(safe_configuration.get("oidc_enabled", False)),
        "tls_verification_enabled": bool(safe_configuration.get("tls_verification_enabled", True)),
        "environment_mode": safe_configuration.get("environment_mode", "unknown"),
    }
    digest = hashlib.sha256(json.dumps(allowed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0",
        "fingerprint": f"sha256:{digest}",
        "drift_state": "unknown",
        "changed_categories": [],
        "indicators": allowed,
        **identities(),
    }


def maintenance_view() -> dict[str, Any]:
    return {
        "state": "normal",
        "reason_code": "NO_MAINTENANCE_DECLARED",
        "start": None,
        "expected_end": None,
        "affected_platform_areas": [],
        "operator_note_reference": None,
    }


def known_issues_view(filters: dict[str, str]) -> dict[str, Any]:
    issues = _yaml("docs/operations/known-issues.yaml").get("issues", [])
    for key, field in (("version", "affected_versions"), ("component", "affected_component"), ("state", "state")):
        if filters.get(key):
            issues = [item for item in issues if item.get(field) == filters[key]]
    return {"items": issues[:100], "count": min(len(issues), 100)}


def readiness_view() -> dict[str, Any]:
    document = _yaml("docs/operations/platform-operational-readiness.yaml")
    return {
        "state": document["overall_state"],
        "categories": [
            {"category": k, "state": v["state"], "evidence": v["evidence"]} for k, v in document["categories"].items()
        ],
    }
