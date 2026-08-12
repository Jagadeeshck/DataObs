#!/usr/bin/env python3
"""Fail-closed validators for first-supported-platform release evidence.

This module aggregates the existing Team 0 evidence contracts.  It does not
produce certification: absent, simulated, stale, or mismatched evidence stays a
release blocker.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
PASS = "PASS"


def verify_evidence(items: list[dict[str, Any]], expected_sha: str, now: datetime) -> list[str]:
    """Return stable reason codes for evidence that cannot certify a release."""
    if not items:
        return ["inventory:MISSING_EVIDENCE"]
    failures: list[str] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        category = str(item.get("evidence_category", "missing"))
        key = (category, str(item.get("artifact_name", "")))
        if key in seen:
            failures.append(f"{category}:DUPLICATE_EVIDENCE")
        seen.add(key)
        if item.get("exact_sha") != expected_sha:
            failures.append(f"{category}:WRONG_SHA")
        expires = item.get("expires_at")
        if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) < now:
            failures.append(f"{category}:STALE_EVIDENCE")
        if item.get("evidence_class") == "FUNCTIONAL_SIMULATION" and item.get("hosted_required"):
            failures.append(f"{category}:SIMULATION_NOT_HOSTED")
        if item.get("status") != "pass":
            failures.append(f"{category}:REQUIRED_SCENARIO_NOT_PASSING")
        path = item.get("path")
        checksum = item.get("checksum")
        if path and checksum:
            actual = "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if actual != checksum:
                failures.append(f"{category}:CHECKSUM_MISMATCH")
        elif item.get("status") == "pass":
            failures.append(f"{category}:MISSING_CHECKSUM")
    return sorted(set(failures))


def verify_artifacts(manifest: dict[str, Any], installed: dict[str, Any] | None = None) -> list[str]:
    failures: list[str] = []
    for image in manifest.get("images", []):
        if image.get("tag") == "latest" or not DIGEST.fullmatch(str(image.get("digest", ""))):
            failures.append("MUTABLE_OR_MISSING_IMAGE_DIGEST")
        if image.get("build_sha") != manifest.get("git_sha"):
            failures.append("IMAGE_BUILD_SHA_MISMATCH")
    if manifest.get("chart_digest") and not DIGEST.fullmatch(str(manifest["chart_digest"])):
        failures.append("INVALID_CHART_DIGEST")
    if installed is not None:
        for field in ("chart_digest", "git_sha", "terminal_migration"):
            if installed.get(field) != manifest.get(field):
                failures.append(f"INSTALLED_{field.upper()}_MISMATCH")
        expected = {x["repository"]: x["digest"] for x in manifest.get("images", [])}
        if installed.get("image_digests") != expected:
            failures.append("INSTALLED_IMAGE_DIGEST_MISMATCH")
        for check in ("readiness", "authentication", "tenant_isolation"):
            if installed.get(check) != "pass":
                failures.append(f"INSTALL_{check.upper()}_FAILED")
    return sorted(set(failures))


def verify_supply_chain(report: dict[str, Any], now: datetime) -> list[str]:
    failures: list[str] = []
    for required in ("sbom", "provenance", "signature"):
        if report.get(required) != "valid":
            failures.append(f"INVALID_OR_MISSING_{required.upper()}")
    if report.get("critical_vulnerabilities", 0) or report.get("high_vulnerabilities", 0):
        failures.append("UNWAIVED_HIGH_OR_CRITICAL_VULNERABILITY")
    for waiver in report.get("waivers", []):
        if datetime.fromisoformat(waiver["expires_at"].replace("Z", "+00:00")) < now:
            failures.append("EXPIRED_VULNERABILITY_WAIVER")
    if report.get("license_policy") not in {"pass", "not_applicable"}:
        failures.append("LICENSE_POLICY_FAILED")
    return sorted(set(failures))


def evaluate_profile(profile: dict[str, Any], gates: list[dict[str, Any]]) -> str:
    """Promote only when every mandatory profile gate is a machine PASS."""
    name = profile["candidate_profile"]
    mandatory = [g for g in gates if name in g.get("mandatory_profiles", [])]
    if not mandatory or any(g.get("result") != PASS for g in mandatory):
        return "incomplete"
    if profile.get("ha_profile") not in {"development", "standard-ha", "production-ha"}:
        return "ineligible"
    return "eligible"


def validate_identity(sha: str) -> None:
    if not SHA.fullmatch(sha):
        raise ValueError("candidate SHA must be an exact lowercase 40-character SHA")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_identity(args.expected_sha)
    data = json.loads(args.index.read_text())
    failures = verify_evidence(data["evidence"], args.expected_sha, datetime.now(timezone.utc))
    result = {
        "schema_version": "1.0",
        "expected_sha": args.expected_sha,
        "verifier": "scripts/release/first_supported_platform.py",
        "result": "pass" if not failures else "fail",
        "failures": failures,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
