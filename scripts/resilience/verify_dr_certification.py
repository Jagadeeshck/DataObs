#!/usr/bin/env python3
"""Fail-closed validator for Team 0 dependency/DR retained evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPORTS = (
    "topology",
    "elasticsearch-latency",
    "elasticsearch-outage",
    "elasticsearch-overload",
    "elasticsearch-resource-failure",
    "oidc-resilience",
    "jwks-rotation",
    "telemetry-outage",
    "dns-resilience",
    "ingress-resilience",
    "upgrade",
    "rollback",
    "migration-failure",
    "migration-exclusivity",
    "backup",
    "restore",
    "control-plane-restore",
    "recovery-point",
    "recovery-time",
    "dr-rehearsal",
    "multi-cluster-isolation",
    "fencing",
    "redaction",
)
LEVELS = {"LEVEL_1_STATIC", "LEVEL_2_FUNCTIONAL", "LEVEL_3_HOSTED", "LEVEL_4_CLOUD_DR"}
PRODUCTION = {"hosted", "cloud-dr"}
REQUIRED = {
    "development": {"topology", "redaction"},
    "functional": set(REPORTS),
    "hosted": set(REPORTS),
    "cloud-dr": set(REPORTS),
}


def read_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root must be an object")
        return value
    except Exception as exc:
        errors.append(f"invalid JSON {path.name}: {exc}")
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--profile", choices=("development", "functional", "hosted", "cloud-dr"), required=True)
    args = parser.parse_args()
    errors: list[str] = []
    if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
        errors.append("--sha must be an exact 40-character lowercase commit SHA")
    manifest_path = args.evidence / "evidence.json"
    manifest = read_json(manifest_path, errors) if manifest_path.is_file() else {}
    if not manifest_path.is_file():
        errors.append("missing evidence.json")
    if manifest.get("exact_sha") != args.sha or manifest.get("profile") != args.profile:
        errors.append("manifest SHA/profile mismatch")
    if manifest.get("security_mode") != "secured":
        errors.append("security mode is not secured")
    if manifest.get("environment") not in {"test", "disposable"}:
        errors.append("evidence is not from a disposable test environment")
    if manifest.get("evidence_level") not in LEVELS:
        errors.append("invalid evidence level")
    if args.profile in PRODUCTION and manifest.get("evidence_level") not in {"LEVEL_3_HOSTED", "LEVEL_4_CLOUD_DR"}:
        errors.append("production profile requires retained hosted evidence")

    reports: dict[str, dict] = {}
    for name in REPORTS:
        path = args.evidence / f"{name}-report.json"
        if not path.is_file():
            if name in REQUIRED[args.profile]:
                errors.append(f"missing {path.name}")
            continue
        report = reports[name] = read_json(path, errors)
        if report.get("exact_sha") != args.sha:
            errors.append(f"identity mismatch: {path.name}")
        if name in REQUIRED[args.profile] and report.get("outcome") in {None, "skipped", "pending"}:
            errors.append(f"mandatory scenario not executed: {name}")
        if (
            name in REQUIRED[args.profile]
            and report.get("outcome") != "passed"
            and not (
                name == "rollback"
                and report.get("outcome") == "rollback_blocked_by_migration"
                and report.get("tooling_prevented_unsafe_rollback") is True
            )
        ):
            errors.append(f"mandatory scenario not passed: {name}")

    required_facts = {
        "backup": ("snapshot_status", "SUCCESS"),
        "restore": ("restore_verified", True),
        "control-plane-restore": ("tenant_isolation_verified", True),
        "upgrade": ("retained_source_release", None),
        "recovery-point": ("observed_data_loss_window_seconds", None),
        "recovery-time": ("observed_recovery_time_seconds", None),
        "redaction": ("redaction_verified", True),
    }
    if args.profile != "development":
        for report_name, (field, expected) in required_facts.items():
            value = reports.get(report_name, {}).get(field)
            if value is None or (expected is not None and value != expected):
                errors.append(f"{report_name} missing/invalid {field}")
    topology = reports.get("topology", {})
    if args.profile != "development" and not topology.get("installation_count", 0) >= 2:
        errors.append("topology does not contain two installations")
    if (
        args.profile != "development"
        and reports.get("multi-cluster-isolation", {}).get("tenant_isolation_verified") is not True
    ):
        errors.append("multi-installation tenant isolation is not verified")

    checksums = args.evidence / "checksums.sha256"
    if not checksums.is_file():
        errors.append("missing checksums.sha256")
    else:
        for line in checksums.read_text(encoding="utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                errors.append("malformed checksum line")
                continue
            target = args.evidence / parts[1].lstrip("* ")
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != parts[0]:
                errors.append(f"checksum mismatch: {parts[1]}")

    summary = {
        "exact_sha": args.sha,
        "profile": args.profile,
        "release_decision": "NO_GO" if errors else "GO",
        "errors": sorted(set(errors)),
    }
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / "certification-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
