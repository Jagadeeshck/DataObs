#!/usr/bin/env python3
"""Build a local/hosted certification evidence manifest from retained artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from packages.elastic_store.manifest import DATA_PRODUCT_RECONCILIATION_EVIDENCE  # noqa: E402

REQUIRED_JOBS = {
    "data-product-reconciliation-contracts",
    "data-product-reconciliation-unit",
    "data-product-reconciliation-elasticsearch",
    "data-product-reconciliation-security",
}


def _validate_inventory(root: Path) -> tuple[list[Path], dict[str, dict]]:
    files = [path for path in root.rglob("*") if path.is_file()]
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name, []).append(path)
    duplicates = sorted(name for name, paths in by_name.items() if len(paths) > 1)
    if duplicates:
        raise ValueError(f"duplicate ambiguous artifact names: {', '.join(duplicates)}")
    missing = [name for name in DATA_PRODUCT_RECONCILIATION_EVIDENCE if name not in by_name]
    if missing:
        raise ValueError(f"missing required artifacts: {', '.join(missing)}")
    empty = [name for name in DATA_PRODUCT_RECONCILIATION_EVIDENCE if by_name[name][0].stat().st_size == 0]
    if empty:
        raise ValueError(f"empty required artifacts: {', '.join(empty)}")

    scenarios: dict[str, dict] = {}
    for name in DATA_PRODUCT_RECONCILIATION_EVIDENCE:
        path = by_name[name][0]
        if name.endswith(".xml"):
            suite = ElementTree.parse(path).getroot()
            failures = sum(
                int(node.attrib.get("failures", 0)) for node in suite.iter() if node.tag in {"testsuite", "testsuites"}
            )
            errors = sum(
                int(node.attrib.get("errors", 0)) for node in suite.iter() if node.tag in {"testsuite", "testsuites"}
            )
            if failures or errors:
                raise ValueError(f"JUnit contains failures/errors: {name}")
        elif name.endswith(".json"):
            value = json.loads(path.read_text())
            required = {
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
            if value["result"] != "passed":
                raise ValueError(f"scenario not passed: {name}")
            if value["elasticsearch_version"] != "9.4.2":
                raise ValueError(f"wrong Elasticsearch version: {name}")
            scenarios[name] = value
    return files, scenarios


def _job_results() -> dict[str, str]:
    jobs = json.loads(os.getenv("CERTIFICATION_JOB_RESULTS", "{}"))
    missing = REQUIRED_JOBS - jobs.keys()
    failed = sorted(name for name in REQUIRED_JOBS if jobs.get(name) != "success")
    if missing or failed:
        raise ValueError(f"missing or failed job conclusions: missing={sorted(missing)}, failed={failed}")
    return jobs


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        raise ValueError(f"evidence directory does not exist: {root}")
    retained, scenarios = _validate_inventory(root)
    jobs = _job_results()
    artifacts = []
    for path in sorted(retained):
        if path.is_symlink():
            raise ValueError(f"symlinks are not retained evidence: {path.relative_to(root)}")
        if path.is_file() and path.name not in {"certification-evidence.json", "manifest.json", ".gitkeep"}:
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
        "repository": os.getenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs"),
        "commit_sha": os.getenv("GITHUB_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "workflow_run_id": run_id,
        "workflow_name": os.getenv("GITHUB_WORKFLOW", "Data Product reconciliation certification"),
        "workflow_run_url": (
            f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.getenv('GITHUB_REPOSITORY', 'Jagadeeshck/DataObs')}/actions/runs/{run_id}"
            if run_id
            else None
        ),
        "jobs": jobs,
        "retention_days": int(os.getenv("CERTIFICATION_RETENTION_DAYS", "30")),
        "review_threads": [
            "PRRT_kwDOR7DqAc6TC7tK",
            "PRRT_kwDOR7DqAc6TC7tQ",
            "PRRT_kwDOR7DqAc6TC7tT",
            "PRRT_kwDOR7DqAc6TC7tW",
            "PRRT_kwDOR7DqAc6TAYAv",
            "PRRT_kwDOR7DqAc6S7Ox6",
            "PRRT_kwDOR7DqAc6S7Ox-",
            "PR-133-runtime",
            "PR-132-runtime",
            "PR-131-runtime",
            "PR-127-P1",
            "PR-125-P1",
            "PR-118-P1",
        ],
        "started_at": os.getenv("CERTIFICATION_STARTED_AT", now),
        "completed_at": now,
        "versions": {
            "elasticsearch": "9.4.2",
            "kibana": "9.4.2",
            "postgresql": "16.9",
            "kafka": "3.9.0",
            "confluent": "7.9.0",
            "otel": "0.139.0",
        },
        "profiles": [os.getenv("CERTIFICATION_PROFILE", "full")],
        "capabilities": {},
        "security": {"status": "complete", "evidence": "security-report.json"},
        "browser": {"status": "not_applicable"},
        "migrations": {
            "status": "complete",
            "evidence": ["migration-clean-install.json", "migration-upgrade.json", "migration-repeat-apply.json"],
        },
        "redaction": {"status": "complete", "evidence": ["sentinel-report.json", "redacted.log"]},
        "scenarios": {name: value["result"] for name, value in sorted(scenarios.items())},
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
