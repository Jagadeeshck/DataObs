"""Canonical, fail-closed compatibility and upgrade decisions for DataObs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


class SupportState(StrEnum):
    SUPPORTED = "supported"
    COMPATIBLE_UNVALIDATED = "compatible_but_unvalidated"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class ReadinessState(StrEnum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class RollbackState(StrEnum):
    SUPPORTED = "supported"
    APPLICATION_ONLY = "application_only"
    BLOCKED_MIGRATION = "blocked_by_migration"
    BLOCKED_CONFIGURATION = "blocked_by_configuration"
    NOT_APPLICABLE = "not_applicable"
    UNVALIDATED = "unvalidated"


@dataclass(frozen=True)
class PlatformProfile:
    dataobs: str
    helm: str
    kubernetes: str
    elasticsearch: str
    python: str
    node: str
    oidc_profile: str
    environment_schema: str
    helm_values_schema: str
    api: str
    migration: str


@dataclass
class ReadinessResult:
    state: ReadinessState
    reason_codes: list[str] = field(default_factory=list)
    rollback: RollbackState = RollbackState.UNVALIDATED
    plan: list[str] = field(default_factory=list)


def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(value)
    if not match:
        raise ValueError(f"invalid SemVer: {value}")
    return tuple(map(int, match.groups()[:3]))  # type: ignore[return-value]


def change_level(source: str, target: str) -> str:
    old, new = parse_semver(source), parse_semver(target)
    if new < old:
        return "downgrade"
    if new[0] != old[0]:
        return "major"
    if new[1] != old[1]:
        return "minor"
    return "patch"


def load_policy(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or ROOT / "docs/release/compatibility-matrix.yaml").read_text())


def classify_version(dimension: str, version: str, policy: dict[str, Any] | None = None) -> SupportState:
    entries = (policy or load_policy())["dimensions"][dimension]
    v = parse_semver(version)
    for item in entries:
        exact = item.get("exact")
        if exact and parse_semver(str(exact)) == v:
            return SupportState(item["state"])
        minimum, maximum = item.get("minimum"), item.get("maximum")
        if minimum and maximum and parse_semver(str(minimum)) <= v <= parse_semver(str(maximum)):
            return SupportState(item["state"])
    return SupportState.UNKNOWN


def classify_rollback(metadata: Iterable[dict[str, Any]], configuration: str = "non_breaking") -> RollbackState:
    items = list(metadata)
    if configuration == "breaking":
        return RollbackState.BLOCKED_CONFIGURATION
    if not items:
        return RollbackState.NOT_APPLICABLE
    if any(item.get("rollback_barrier") or item.get("destructive") for item in items):
        return RollbackState.BLOCKED_MIGRATION
    if any(item.get("classification") in {None, "unknown"} for item in items):
        return RollbackState.UNVALIDATED
    if all(item.get("application_backward_compatible") for item in items):
        return RollbackState.SUPPORTED
    return RollbackState.APPLICATION_ONLY


def assess_upgrade(source: PlatformProfile, target: PlatformProfile, evidence: dict[str, Any]) -> ReadinessResult:
    reasons: list[str] = []
    try:
        level = change_level(source.dataobs, target.dataobs)
    except ValueError:
        return ReadinessResult(ReadinessState.BLOCKED, ["UNSUPPORTED_TARGET_VERSION"])
    if level in {"major", "downgrade"}:
        reasons.append("UNSUPPORTED_TARGET_VERSION")
    for dimension, value, code in (
        ("elasticsearch", target.elasticsearch, "ELASTICSEARCH_VERSION_INCOMPATIBLE"),
        ("kubernetes", target.kubernetes, "KUBERNETES_VERSION_INCOMPATIBLE"),
        ("helm", target.helm, "HELM_VERSION_INCOMPATIBLE"),
    ):
        state = classify_version(dimension, value)
        if state == SupportState.INCOMPATIBLE:
            reasons.append(code)
        elif state != SupportState.SUPPORTED:
            reasons.append("CERTIFICATION_EVIDENCE_MISSING")
    if evidence.get("migration_graph") != "valid":
        reasons.append("MIGRATION_GRAPH_INVALID")
    if evidence.get("migration_state") != source.migration:
        reasons.append("MIGRATION_PENDING")
    if evidence.get("configuration") == "breaking":
        reasons.append("CONFIGURATION_BREAKING_CHANGE")
    if evidence.get("known_issue_blocks"):
        reasons.append("KNOWN_ISSUE_BLOCKS_UPGRADE")
    if evidence.get("backup_required") and not evidence.get("fresh_backup_manifest"):
        reasons.append("BACKUP_STALE")
    if not evidence.get("restore_validated"):
        reasons.append("RESTORE_UNVALIDATED")
    if not evidence.get("certification_passed"):
        reasons.append("CERTIFICATION_EVIDENCE_MISSING")
    rollback = classify_rollback(evidence.get("migrations", []), evidence.get("configuration", "unknown"))
    if rollback in {RollbackState.BLOCKED_MIGRATION, RollbackState.BLOCKED_CONFIGURATION, RollbackState.UNVALIDATED}:
        reasons.append("ROLLBACK_UNAVAILABLE")
    reasons = list(dict.fromkeys(reasons))
    blocking = any(code != "CERTIFICATION_EVIDENCE_MISSING" for code in reasons)
    state = ReadinessState.BLOCKED if blocking else (ReadinessState.UNKNOWN if reasons else ReadinessState.READY)
    return ReadinessResult(
        state,
        reasons,
        rollback,
        [
            "preflight",
            "backup",
            "maintenance",
            "update",
            "migration",
            "readiness",
            "smoke",
            "rollback-assessment",
            "maintenance-exit",
        ],
    )


def compatibility_fingerprint(profile: PlatformProfile) -> str:
    payload = {**profile.__dict__, "policy": load_policy()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
