#!/usr/bin/env python3
"""Build a local/hosted certification evidence manifest from retained artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from packages.elastic_store.manifest import (  # noqa: E402
    DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE,
    DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES,
    DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE,
    data_product_evidence_inventory,
)

FOUNDATION_JOBS = {
    "data-product-reconciliation-contracts",
    "data-product-reconciliation-unit",
    "data-product-foundation-elasticsearch",
    "data-product-foundation-security",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SUPPORTED_REPORT_SCHEMAS = {"1.0"}


def _junit_summary(path: Path) -> dict:
    root = ElementTree.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(s.attrib.get("tests", 0)) for s in suites)
    failures = sum(int(s.attrib.get("failures", 0)) for s in suites)
    errors = sum(int(s.attrib.get("errors", 0)) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", 0)) for s in suites)
    if tests == 0 or failures or errors:
        raise ValueError(f"JUnit is empty or contains failures/errors: {path.name}")
    policy = DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES.get(
        path.name, {"allow_skips": False, "allowed_skip_reasons": (), "maximum_skips": 0}
    )
    skip_reasons = []
    for case in root.iter("testcase"):
        for skip in case.findall("skipped"):
            reason = (skip.attrib.get("message") or skip.text or "").strip()
            if not reason:
                raise ValueError(f"skipped JUnit case has no reason: {path.name}")
            skip_reasons.append(reason)
    if len(skip_reasons) != skipped:
        raise ValueError(f"JUnit skip count does not match skipped cases: {path.name}")
    if skipped and not policy["allow_skips"]:
        raise ValueError(f"JUnit policy forbids skips: {path.name}")
    if skipped > policy["maximum_skips"]:
        raise ValueError(f"JUnit skip count exceeds policy: {path.name}")
    unknown = sorted({reason for reason in skip_reasons if reason not in policy["allowed_skip_reasons"]})
    if unknown:
        raise ValueError(f"JUnit contains unapproved skip reasons: {path.name}: {unknown}")
    return {
        "suite": root.attrib.get("name", path.stem),
        "tests": tests,
        "passed": tests - failures - errors - skipped,
        "failed": failures,
        "errors": errors,
        "skipped": skipped,
        "skip_reasons": sorted(set(skip_reasons)),
        "policy": policy,
    }


def _validate_scenario(name: str, value: dict) -> None:
    required = {
        "schema_version",
        "scenario",
        "commit_sha",
        "elasticsearch_version",
        "started_at",
        "completed_at",
        "test_names",
        "assertion_summary",
        "redacted_references",
        "result",
    }
    absent = required - value.keys()
    if absent:
        raise ValueError(f"scenario fields missing from {name}: {', '.join(sorted(absent))}")
    if not SHA_RE.fullmatch(value["commit_sha"]):
        raise ValueError(f"invalid commit SHA: {name}")
    if os.getenv("GITHUB_SHA") and value["commit_sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError(f"hosted commit SHA mismatch: {name}")
    if not value["test_names"] or not value["assertion_summary"] or value["result"] != "passed":
        raise ValueError(f"scenario is empty or not passed: {name}")
    if value["elasticsearch_version"] != "9.4.2":
        raise ValueError(f"wrong Elasticsearch version: {name}")
    start = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
    complete = datetime.fromisoformat(value["completed_at"].replace("Z", "+00:00"))
    if start > complete:
        raise ValueError(f"scenario timestamps are reversed: {name}")


def _validate_report_provenance(name: str, value: dict, *, require_elasticsearch: bool = True) -> None:
    """Apply the same fail-closed provenance checks to every special report."""
    if value.get("schema_version") not in SUPPORTED_REPORT_SCHEMAS:
        raise ValueError(f"unsupported schema version: {name}")
    if not SHA_RE.fullmatch(str(value.get("commit_sha", ""))):
        raise ValueError(f"invalid commit SHA: {name}")
    if os.getenv("GITHUB_SHA") and value["commit_sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError(f"hosted commit SHA mismatch: {name}")
    if require_elasticsearch and value.get("elasticsearch_version") != "9.4.2":
        raise ValueError(f"wrong Elasticsearch version: {name}")
    try:
        start = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
        complete = datetime.fromisoformat(value["completed_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid report timestamps: {name}") from exc
    if start.tzinfo is None or complete.tzinfo is None or start > complete:
        raise ValueError(f"report timestamps are reversed or timezone-naive: {name}")
    if value.get("result") != "passed":
        raise ValueError(f"report is not passed: {name}")


def _validate_inventory(root: Path, inventory: tuple[str, ...]) -> tuple[list[Path], dict[str, dict], dict[str, dict]]:
    files = [path for path in root.rglob("*") if path.is_file()]
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name, []).append(path)
    duplicates = sorted(name for name, paths in by_name.items() if len(paths) > 1)
    if duplicates:
        raise ValueError(f"duplicate ambiguous artifact names: {', '.join(duplicates)}")
    missing = [name for name in inventory if name not in by_name]
    if missing:
        raise ValueError(f"missing required artifacts: {', '.join(missing)}")
    empty = [name for name in inventory if by_name[name][0].stat().st_size == 0]
    if empty:
        raise ValueError(f"empty required artifacts: {', '.join(empty)}")

    scenarios: dict[str, dict] = {}
    junit: dict[str, dict] = {}
    for name in inventory:
        path = by_name[name][0]
        if name.endswith(".xml"):
            junit[name] = _junit_summary(path)
        elif name.endswith(".json"):
            value = json.loads(path.read_text())
            if name == "security-report.json":
                required = {
                    "schema_version",
                    "commit_sha",
                    "elasticsearch_version",
                    "started_at",
                    "completed_at",
                    "scenario_count",
                    "passed_count",
                    "failed_count",
                    "controls",
                    "test_names",
                    "redacted_references",
                    "result",
                }
                if (
                    required - value.keys()
                    or value["failed_count"]
                    or value["passed_count"] != value["scenario_count"]
                    or not value["controls"]
                    or value["scenario_count"] <= 0
                    or not value["test_names"]
                    or value["result"] != "passed"
                ):
                    raise ValueError("invalid security report")
                _validate_report_provenance(name, value)
                continue
            if name == "sentinel-report.json":
                required = {
                    "schema_version",
                    "commit_sha",
                    "elasticsearch_version",
                    "started_at",
                    "completed_at",
                    "files_scanned",
                    "sentinels_injected",
                    "sentinels_redacted",
                    "sentinels_remaining",
                    "test_names",
                    "result",
                }
                if (
                    required - value.keys()
                    or value["sentinels_injected"] <= 0
                    or value["files_scanned"] <= 0
                    or value["sentinels_remaining"]
                    or value["sentinels_redacted"] != value["sentinels_injected"]
                    or value["result"] != "passed"
                    or not value["test_names"]
                ):
                    raise ValueError("invalid sentinel report")
                _validate_report_provenance(name, value)
                continue
            _validate_scenario(name, value)
            scenarios[name] = value
    return files, scenarios, junit


def _job_results(required_jobs: set[str]) -> dict[str, str]:
    jobs = json.loads(os.getenv("CERTIFICATION_JOB_RESULTS", "{}"))
    missing = required_jobs - jobs.keys()
    failed = sorted(name for name in required_jobs if jobs.get(name) != "success")
    if missing or failed:
        raise ValueError(f"missing or failed job conclusions: missing={sorted(missing)}, failed={failed}")
    return jobs


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        raise ValueError(f"evidence directory does not exist: {root}")
    profile = os.getenv("DATA_PRODUCT_CERTIFICATION_PROFILE")
    if not profile:
        raise ValueError("DATA_PRODUCT_CERTIFICATION_PROFILE must be explicit")
    inventory = data_product_evidence_inventory(profile)
    retained, scenarios, junit = _validate_inventory(root, inventory)
    expected_junit = (
        set(DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE)
        if profile == DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE
        else {name for name in inventory if name.endswith(".xml")}
    )
    if set(junit) != expected_junit:
        raise ValueError(f"JUnit inventory mismatch: expected={sorted(expected_junit)}, actual={sorted(junit)}")
    required_jobs = (
        FOUNDATION_JOBS
        if profile == DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE
        else {
            "data-product-reconciliation-contracts",
            "data-product-reconciliation-unit",
            "data-product-reconciliation-elasticsearch",
            "data-product-reconciliation-security",
        }
    )
    jobs = _job_results(required_jobs)
    artifacts = []
    for path in sorted(retained):
        if path.is_symlink():
            raise ValueError(f"symlinks are not retained evidence: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        if (
            path.is_file()
            and relative not in {"certification-evidence.json", "manifest.json"}
            and path.name != ".gitkeep"
        ):
            artifacts.append(
                {
                    "name": path.name,
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    run_id = os.getenv("GITHUB_RUN_ID")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc = {
        "schema_version": "1.0",
        "certification_profile": profile,
        "certification_statement": "Hosted runtime foundation only; full reconciliation certification is not claimed.",
        "full_reconciliation_certified": False,
        "release_readiness": "blocked",
        "repository": os.getenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs"),
        "commit_sha": os.getenv("GITHUB_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "workflow_run_id": run_id,
        "workflow_name": os.getenv("GITHUB_WORKFLOW", "Data Product hosted certification foundation"),
        "workflow_run_url": (
            f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.getenv('GITHUB_REPOSITORY', 'Jagadeeshck/DataObs')}/actions/runs/{run_id}"
            if run_id
            else None
        ),
        "jobs": jobs,
        "retention_days": int(os.getenv("CERTIFICATION_RETENTION_DAYS", "30")),
        "review_threads": (
            [
                "PRRT_kwDOR7DqAc6TMAAg",
                "PRRT_kwDOR7DqAc6TMAAl",
                "PRRT_kwDOR7DqAc6TMAAt",
                "PRRT_kwDOR7DqAc6TLY0H",
                "PRRT_kwDOR7DqAc6TLAAP",
                "PRRT_kwDOR7DqAc6TLAAS",
                "PRRT_kwDOR7DqAc6TLAAX",
            ]
            if profile == DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE
            else []
        ),
        "started_at": os.getenv("CERTIFICATION_STARTED_AT", now),
        "completed_at": now,
        "versions": {"elasticsearch": "9.4.2", "python": sys.version.split()[0]},
        "profiles": [profile],
        "capabilities": {},
        "security": {"status": "complete", "evidence": "security-report.json"},
        "browser": {"status": "not_applicable"},
        "migrations": {
            "status": "complete",
            "evidence": ["migration-clean-install.json", "migration-upgrade.json", "migration-repeat-apply.json"],
        },
        "redaction": {"status": "complete", "evidence": ["sentinel-report.json", "redacted.log"]},
        "scenarios": {name: value["result"] for name, value in sorted(scenarios.items())},
        "junit": junit,
        "artifacts": artifacts,
    }
    encoded = json.dumps(doc, indent=2) + "\n"
    # Keep the historical generic filename while the Data Product workflow
    # publishes the required resource-specific manifest.
    (root / "certification-evidence.json").write_text(encoded)
    (root / "manifest.json").write_text(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
