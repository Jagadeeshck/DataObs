#!/usr/bin/env python3
"""Build and independently verify the generic CI certification aggregate.

This is intentionally separate from the Data Product evidence manifest.  It
aggregates the focused CI certification jobs without reinterpreting their
artifacts as a Team 2 Data Product profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from scripts.certification.validate_job_results import REQUIRED_JOBS

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_BYTES = 100 * 1024 * 1024
MANIFEST = "ci-certification-summary.json"
ARTIFACT_DIRS = {
    "contracts": "contracts",
    "migrations-incidents": "migrations-incidents",
    "postgres": "postgres",
    "kafka": "kafka",
    "openlineage-product": "openlineage-product",
    "browser": "browser",
    "security": "security",
}
SENTINELS = (
    b"DATAOBS_CERT_SENTINEL_DB_PASSWORD",
    b"DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
    b"DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
    b"DATAOBS_CERT_SENTINEL_API_KEY",
)


def _required_files(root: Path, required_jobs: set[str]) -> list[Path]:
    files: list[Path] = []
    for job in sorted(required_jobs):
        directory = root / ARTIFACT_DIRS[job]
        if not directory.is_dir():
            raise ValueError(f"required certification artifact directory is missing: {ARTIFACT_DIRS[job]}")
        owned = sorted(path for path in directory.rglob("*") if path.is_file())
        if not owned:
            raise ValueError(f"required certification artifact is empty: {ARTIFACT_DIRS[job]}")
        files.extend(owned)
    job_results = root / "job-results.json"
    if not job_results.is_file():
        raise ValueError("job-results.json is missing")
    files.append(job_results)
    return sorted(set(files))


def _junit(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() != ".xml":
        return None
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    if not suites:
        return None
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, "0") or 0)
    if totals["tests"] <= 0:
        raise ValueError(f"JUnit has no executed tests: {path.name}")
    if totals["failures"] or totals["errors"] or totals["skipped"]:
        raise ValueError(f"JUnit is not clean: {path.name}: {totals}")
    return totals


def _inventory(root: Path, required_jobs: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = _required_files(root, required_jobs)
    inventory: list[dict[str, Any]] = []
    junit: list[dict[str, Any]] = []
    for path in files:
        if path.is_symlink():
            raise ValueError(f"symlink is forbidden: {path.relative_to(root)}")
        size = path.stat().st_size
        if size <= 0:
            raise ValueError(f"empty retained artifact: {path.relative_to(root)}")
        if size > MAX_BYTES:
            raise ValueError(f"artifact exceeds 100 MiB: {path.relative_to(root)}")
        raw = path.read_bytes()
        if any(value in raw for value in SENTINELS):
            raise ValueError(f"unredacted certification sentinel remains: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        inventory.append(
            {
                "path": relative,
                "bytes": size,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        summary = _junit(path)
        if summary is not None:
            junit.append({"path": relative, **summary})
    for job in required_jobs - {"browser"}:
        prefix = ARTIFACT_DIRS[job] + "/"
        if not any(item["path"].startswith(prefix) for item in junit):
            raise ValueError(f"required certification job has no JUnit evidence: {job}")
    return inventory, junit


def build(root: Path, scope: str, target_sha: str) -> dict[str, Any]:
    if scope not in REQUIRED_JOBS:
        raise ValueError(f"unsupported certification scope: {scope}")
    if not SHA_RE.fullmatch(target_sha):
        raise ValueError("target SHA must be an exact lowercase 40-character SHA")
    results = json.loads((root / "job-results.json").read_text())
    if results.get("scope") != scope or results.get("errors"):
        raise ValueError("job result policy did not pass for requested scope")
    required = set(results.get("required_jobs", []))
    if required != set(REQUIRED_JOBS[scope]):
        raise ValueError("job result required-job set does not match canonical scope policy")
    inventory, junit = _inventory(root, required)
    run_id = os.getenv("GITHUB_RUN_ID")
    attempt = os.getenv("GITHUB_RUN_ATTEMPT")
    document = {
        "schema_version": "1.0",
        "repository": os.getenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs"),
        "target_sha": target_sha,
        "workflow": os.getenv("GITHUB_WORKFLOW", "CI"),
        "workflow_run_id": int(run_id) if run_id else None,
        "workflow_run_attempt": int(attempt) if attempt else None,
        "event": os.getenv("GITHUB_EVENT_NAME"),
        "scope": scope,
        "required_jobs": sorted(required),
        "job_results": results,
        "junit_summaries": junit,
        "artifact_inventory": inventory,
        "status": "pass",
    }
    (root / MANIFEST).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return document


def verify(root: Path, expected_sha: str) -> list[str]:
    errors: list[str] = []
    path = root / MANIFEST
    if not path.is_file():
        return [f"{MANIFEST} is missing"]
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError:
        return [f"{MANIFEST} is invalid JSON"]
    if document.get("schema_version") != "1.0" or document.get("status") != "pass":
        errors.append("summary manifest schema/status is invalid")
    if document.get("target_sha") != expected_sha or not SHA_RE.fullmatch(str(document.get("target_sha", ""))):
        errors.append("summary manifest target SHA mismatch")
    if document.get("repository") != os.getenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs"):
        errors.append("summary manifest repository mismatch")
    scope = document.get("scope")
    if scope not in REQUIRED_JOBS:
        errors.append("summary manifest scope is invalid")
        return errors
    required = set(document.get("required_jobs", []))
    if required != set(REQUIRED_JOBS[scope]):
        errors.append("summary manifest required-job set mismatch")
    try:
        expected_inventory, expected_junit = _inventory(root, required)
    except (ValueError, ET.ParseError) as exc:
        errors.append(str(exc))
        return errors
    if document.get("artifact_inventory") != expected_inventory:
        errors.append("summary artifact inventory/digests changed after manifest creation")
    if document.get("junit_summaries") != expected_junit:
        errors.append("summary JUnit inventory changed after manifest creation")
    results = document.get("job_results")
    if not isinstance(results, dict) or results.get("errors") or results.get("scope") != scope:
        errors.append("summary job result policy is not passing")
    run_id = document.get("workflow_run_id")
    attempt = document.get("workflow_run_attempt")
    if os.getenv("GITHUB_ACTIONS") == "true":
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
            errors.append("workflow run ID is missing or invalid")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
            errors.append("workflow run attempt is missing or invalid")
        if str(run_id) != os.getenv("GITHUB_RUN_ID"):
            errors.append("workflow run ID does not match verifier run")
        if str(attempt) != os.getenv("GITHUB_RUN_ATTEMPT"):
            errors.append("workflow run attempt does not match verifier run")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("root", type=Path)
    build_parser.add_argument("--scope", required=True)
    build_parser.add_argument("--sha", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("root", type=Path)
    verify_parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "build":
            build(root, args.scope, args.sha)
            print("CI certification summary manifest built")
            return 0
        errors = verify(root, args.expected_sha)
    except (ValueError, ET.ParseError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print("CI certification summary verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
