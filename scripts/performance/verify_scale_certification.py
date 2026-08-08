#!/usr/bin/env python3
"""Fail-closed verifier for retained Team 0 scale/HA certification evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPORTS = [
    "topology",
    "workload",
    "latency",
    "throughput",
    "saturation",
    "noisy-neighbour",
    "autoscaling",
    "worker-scale",
    "worker-crash-matrix",
    "pod-failure",
    "node-failure",
    "soak",
    "resource-leak",
    "elasticsearch-query-budget",
    "elasticsearch-storage-growth",
    "backpressure",
    "redaction",
]
REQUIRED = {
    "development": {"workload", "latency", "throughput", "saturation"},
    "standard-ha": {
        "workload",
        "latency",
        "throughput",
        "saturation",
        "noisy-neighbour",
        "autoscaling",
        "worker-scale",
        "worker-crash-matrix",
        "pod-failure",
        "soak",
        "resource-leak",
        "elasticsearch-query-budget",
        "elasticsearch-storage-growth",
        "backpressure",
        "redaction",
    },
    "production-ha": set(REPORTS),
}


def load(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(f"invalid JSON {path.name}: {exc}") from exc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    p.add_argument("--sha", required=True)
    p.add_argument("--profile", choices=REQUIRED, required=True)
    a = p.parse_args()
    errors = []
    if not re.fullmatch(r"[0-9a-f]{40}", a.sha):
        errors.append("--sha must be an exact 40-character commit SHA")
    manifest_path = a.evidence / "evidence.json"
    if not manifest_path.is_file():
        errors.append("missing evidence.json")
    manifest = load(manifest_path) if manifest_path.is_file() else {}
    workload_hash = manifest.get("workload_hash")
    if not re.fullmatch(r"[0-9a-f]{64}", str(workload_hash or "")):
        errors.append("missing/invalid workload hash")
    if manifest.get("exact_sha") != a.sha or manifest.get("certification_profile") != a.profile:
        errors.append("manifest SHA/profile mismatch")
    for name in REPORTS:
        path = a.evidence / f"{name}-report.json"
        if not path.is_file():
            errors.append(f"missing {path.name}")
            continue
        report = load(path)
        if (
            report.get("exact_sha") != a.sha
            or report.get("certification_profile") != a.profile
            or report.get("workload_hash") != workload_hash
        ):
            errors.append(f"identity mismatch: {path.name}")
        if name in REQUIRED[a.profile] and report.get("outcome") != "passed":
            errors.append(f"mandatory scenario not passed: {name}")
        if (
            name == "noisy-neighbour"
            and a.profile != "development"
            and report.get("tenant_isolation") not in {"isolated", "acceptable_interference"}
        ):
            errors.append("tenant isolation is not proven")
        if (
            name == "soak"
            and a.profile != "development"
            and report.get("soak_class") not in {"short", "medium", "extended"}
        ):
            errors.append("required soak class missing")
    checks = a.evidence / "checksums.sha256"
    if not checks.is_file():
        errors.append("missing checksums.sha256")
    else:
        for line in checks.read_text().splitlines():
            try:
                digest, name = line.split(None, 1)
                target = a.evidence / name.lstrip("* ")
            except ValueError:
                errors.append("malformed checksum line")
                continue
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append(f"checksum mismatch: {name}")
    summary = {
        "exact_sha": a.sha,
        "certification_profile": a.profile,
        "outcome": "failed" if errors else "passed",
        "errors": errors,
    }
    (a.evidence / "certification-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
