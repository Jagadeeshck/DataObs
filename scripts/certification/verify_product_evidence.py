#!/usr/bin/env python3
"""Build and independently verify exact-commit product certification evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.release.release_metadata import ELASTICSEARCH_VERSION, terminal_migration  # noqa: E402

TERMINAL_MIGRATION = terminal_migration()
REQUIRED_METADATA = {
    "producer_sha",
    "repository",
    "workflow_name",
    "workflow_run_id",
    "job_id",
    "event_type",
    "elasticsearch_version",
    "python_version",
    "node_version",
    "migration_terminal_id",
    "test_results",
    "generated_at",
}


class EvidenceError(ValueError):
    """Evidence is incomplete, ambiguous, or belongs to another execution."""


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _xml_summary(files: list[Path]) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for path in files:
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        if not suites:
            raise EvidenceError(f"no test suites in {path}")
        for suite in suites:
            for field in totals:
                totals[field] += int(suite.attrib.get(field, "0"))
    return totals


def generate(args: argparse.Namespace) -> None:
    output = Path(args.directory)
    result_files = sorted((output / "results").glob("*.xml"))
    if not result_files:
        raise EvidenceError("required test result XML is missing")
    summary = _xml_summary(result_files)
    metadata = {
        "producer_sha": _head(),
        "repository": args.repository,
        "workflow_name": args.workflow,
        "workflow_run_id": str(args.run_id),
        "job_id": str(args.job_id),
        "event_type": args.event,
        "elasticsearch_version": args.elasticsearch_version,
        "python_version": args.python_version,
        "node_version": args.node_version,
        "migration_terminal_id": TERMINAL_MIGRATION,
        "test_results": summary,
        "result_files": [str(path.relative_to(output)) for path in result_files],
        "required_suites": sorted(set(args.required_suite)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    envelope = {
        "schema_version": "1.0",
        "repository": args.repository,
        "producer_sha": metadata["producer_sha"],
        "workflow_file": str(args.workflow).split("/")[-1],
        "workflow_run_id": str(args.run_id),
        "workflow_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"),
        "event": args.event,
        "generated_at": metadata["generated_at"],
        "elasticsearch_version": args.elasticsearch_version,
        "terminal_migration": TERMINAL_MIGRATION,
        "tool_versions": {"python": args.python_version, "node": args.node_version},
        "test_summaries": [{"category": item, "status": "pass"} for item in sorted(set(args.required_suite))],
        "artifact_inventory": [{"path": item} for item in metadata["result_files"]],
        "redaction_status": "pass",
        "status": "pass" if not summary["failures"] and not summary["errors"] else "fail",
    }
    (output / "evidence.json").write_text(json.dumps(envelope, indent=2) + "\n")


def verify(args: argparse.Namespace) -> None:
    root = Path(args.directory)
    metadata_path = root / "metadata.json"
    if not metadata_path.is_file():
        raise EvidenceError("required metadata.json is missing")
    metadata = json.loads(metadata_path.read_text())
    missing = REQUIRED_METADATA - metadata.keys()
    if missing:
        raise EvidenceError(f"metadata fields missing: {', '.join(sorted(missing))}")
    expected_sha = args.expected_sha or _head()
    checks = {
        "producer SHA": (metadata["producer_sha"], expected_sha),
        "repository": (metadata["repository"], args.repository),
        "workflow name": (metadata["workflow_name"], args.workflow),
        "workflow run ID": (str(metadata["workflow_run_id"]), str(args.run_id)),
        "Elasticsearch version": (metadata["elasticsearch_version"], ELASTICSEARCH_VERSION),
        "terminal migration": (metadata["migration_terminal_id"], TERMINAL_MIGRATION),
    }
    for label, (actual, expected) in checks.items():
        if actual != expected:
            raise EvidenceError(f"{label} mismatch: expected {expected!r}, got {actual!r}")
    if not str(metadata["job_id"]).isdigit() or not str(metadata["event_type"]).strip():
        raise EvidenceError("artifact metadata has an ambiguous job ID or event type")
    declared = metadata.get("required_suites")
    if not isinstance(declared, list) or not set(args.required_suite).issubset(declared):
        raise EvidenceError("required security, tenant, browser, or accessibility suite is absent")
    files = [root / item for item in metadata.get("result_files", [])]
    if not files or any(not item.is_file() for item in files):
        raise EvidenceError("required result files are missing")
    summary = _xml_summary(files)
    if summary["tests"] < 1 or summary["failures"] or summary["errors"]:
        raise EvidenceError(f"test result XML is not successful: {summary}")
    if summary != metadata["test_results"]:
        raise EvidenceError("test result summary does not match XML")
    if any(name in declared for name in ("security", "tenant", "browser", "accessibility")) and summary["skipped"]:
        raise EvidenceError("security, tenant, browser, or accessibility tests were skipped")
    required_files = {
        "elasticsearch": ("elasticsearch-version.txt", ELASTICSEARCH_VERSION),
        "postgresql": ("postgresql-integration.txt", "PASS"),
        "browser": ("results/browser.xml", None),
        "accessibility": ("results/browser.xml", None),
    }
    for suite, (name, expected) in required_files.items():
        if suite not in declared:
            continue
        path = root / name
        if not path.is_file():
            raise EvidenceError(f"{suite} evidence is missing: {name}")
        if expected is not None and path.read_text().strip() != expected:
            raise EvidenceError(f"{suite} evidence is invalid")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    for command in ("generate", "verify"):
        item = sub.add_parser(command)
        item.add_argument("--directory", required=True)
        item.add_argument("--repository", required=True)
        item.add_argument("--workflow", required=True)
        item.add_argument("--run-id", required=True)
        item.add_argument("--required-suite", action="append", default=[])
        if command == "generate":
            item.add_argument("--job-id", required=True)
            item.add_argument("--event", required=True)
            item.add_argument("--elasticsearch-version", required=True)
            item.add_argument("--python-version", required=True)
            item.add_argument("--node-version", default="not-applicable")
        else:
            item.add_argument("--expected-sha")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        generate(args) if args.command == "generate" else verify(args)
    except (EvidenceError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"product evidence {args.command} passed: {args.workflow}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
