#!/usr/bin/env python3
"""Generate and independently verify Team 2 Sprint 4 E2E evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ELASTICSEARCH_VERSION = "9.4.2"
ARTIFACT_NAME = "e2e-signal-path"
REQUIRED_SCENARIOS = {
    "failed complete path",
    "persistent deduplication",
    "tenant isolation",
    "successful check",
    "partial channel failure",
}
EXPECTED_MAPPING = {
    "dataobs-reliability-status-v1.observed_value": "double",
    "dataobs-data-product-revisions-v1.revision": "integer",
    "dataobs-data-product-revisions-v1.operation_id": "keyword",
    "dataobs-data-product-operation-state-v1.revision": "integer",
    "dataobs-data-product-operation-state-v1.operation_id": "keyword",
}


class EvidenceError(ValueError):
    """The retained Sprint 4 evidence is incomplete or inconsistent."""


def _head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceError(f"required evidence is missing: {path.name}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise EvidenceError(f"evidence must be a JSON object: {path.name}")
    return value


def _junit_summary(path: Path) -> dict[str, int]:
    if not path.is_file():
        raise EvidenceError(f"required JUnit is missing: {path.name}")
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise EvidenceError(f"no test suites in {path.name}")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for field in totals:
            totals[field] += int(suite.attrib.get(field, "0"))
    return totals


def _validate_migration_status(
    first: dict[str, Any],
    second: dict[str, Any],
) -> None:
    if first != second:
        raise EvidenceError("migration status changed after repeated apply")
    if first.get("ready") is not True:
        raise EvidenceError("migration registry is not ready")
    if first.get("missing") or first.get("conflicts"):
        raise EvidenceError("migration registry reports missing or conflicting migrations")
    if first.get("checksum_mismatch"):
        raise EvidenceError("migration registry reports checksum mismatch")
    applied = first.get("applied")
    if not isinstance(applied, dict) or not applied:
        raise EvidenceError("migration applied inventory is empty")
    for migration_id, document in applied.items():
        checksum = document.get("checksum") if isinstance(document, dict) else None
        if not isinstance(checksum, str) or not checksum.strip():
            raise EvidenceError(f"migration checksum is missing for {migration_id}")


def _validate(root: Path, expected_sha: str) -> dict[str, int]:
    signal = _load(root / "signal-path-summary.json")
    otel = _load(root / "otel-correlation.json")
    delivery = _load(root / "alert-delivery-summary.json")
    mapping = _load(root / "mapping-contract.json")
    first_status = _load(root / "migration-status-first.json")
    second_status = _load(root / "migration-status-second.json")

    if signal.get("status") != "passed":
        raise EvidenceError("signal path did not report passed")
    if signal.get("commit_sha") != expected_sha:
        raise EvidenceError("signal-path commit SHA does not match exact certification SHA")
    if signal.get("elasticsearch_version") != ELASTICSEARCH_VERSION:
        raise EvidenceError("signal path did not execute against Elasticsearch 9.4.2")
    if signal.get("tenant") != "signal-tenant-a" or signal.get("environment") != "production":
        raise EvidenceError("signal path scope is not the expected tenant/environment")
    if set(signal.get("scenarios", [])) != REQUIRED_SCENARIOS:
        raise EvidenceError("signal path scenario inventory is incomplete")

    dedupe = signal.get("deduplication")
    if not isinstance(dedupe, dict):
        raise EvidenceError("deduplication evidence is missing")
    if dedupe.get("incident_id") != dedupe.get("replayed_incident_id"):
        raise EvidenceError("incident replay did not deduplicate")
    if dedupe.get("notification_replay_count") != 0:
        raise EvidenceError("incident replay produced duplicate notification delivery")

    if otel.get("execution_id") != signal.get("execution_id"):
        raise EvidenceError("OTel execution correlation does not match signal summary")
    if otel.get("trace_id") != signal.get("trace_id"):
        raise EvidenceError("OTel trace correlation does not match signal summary")

    if delivery.get("credentials_redacted") is not True:
        raise EvidenceError("delivery evidence is not explicitly redaction-safe")
    channels = delivery.get("channels")
    if not isinstance(channels, dict):
        raise EvidenceError("delivery channel outcomes are missing")
    if channels != {
        "slack": "failed",
        "pagerduty": "succeeded",
        "servicenow": "succeeded",
    }:
        raise EvidenceError("partial delivery outcome does not match executed scenario")
    if delivery.get("captured_count") != 3:
        raise EvidenceError("complete-path notification evidence is incomplete")

    if mapping.get("elasticsearch_version") != ELASTICSEARCH_VERSION:
        raise EvidenceError("mapping proof did not execute against Elasticsearch 9.4.2")
    if mapping.get("fields") != EXPECTED_MAPPING:
        raise EvidenceError("Data Product or reliability mapping proof is incorrect")

    _validate_migration_status(first_status, second_status)

    signal_junit = _junit_summary(root / "results" / "signal-path.xml")
    migration_junit = _junit_summary(root / "results" / "data-product-migrations.xml")
    for name, summary in (
        ("signal path", signal_junit),
        ("Data Product migration", migration_junit),
    ):
        if summary["tests"] < 1:
            raise EvidenceError(f"{name} JUnit contains no tests")
        if summary["failures"] or summary["errors"] or summary["skipped"]:
            raise EvidenceError(f"{name} JUnit is not skip-free and successful: {summary}")
    return {
        key: signal_junit[key] + migration_junit[key]
        for key in signal_junit
    }


def generate(args: argparse.Namespace) -> None:
    root = Path(args.directory)
    expected_sha = _head()
    summary = _validate(root, expected_sha)
    metadata = {
        "schema_version": "1.0",
        "artifact": ARTIFACT_NAME,
        "repository": args.repository,
        "workflow": args.workflow,
        "workflow_run_id": str(args.run_id),
        "job_id": str(args.job_id),
        "event": args.event,
        "producer_sha": expected_sha,
        "elasticsearch_version": ELASTICSEARCH_VERSION,
        "test_summary": summary,
        "integration_tests_executed": True,
        "skipped_tests_accepted": False,
        "independent_verification": "required",
    }
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (root / "evidence.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "artifact": ARTIFACT_NAME,
                "producer_sha": expected_sha,
                "status": "pass",
                "test_categories": [
                    "data-product",
                    "elasticsearch",
                    "quality",
                    "otel",
                    "incident",
                    "delivery",
                    "api",
                    "tenant-isolation",
                ],
                "redaction_status": "pass",
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Team 2 Sprint 4 evidence generated for {expected_sha}")


def verify(args: argparse.Namespace) -> None:
    root = Path(args.directory)
    metadata = _load(root / "metadata.json")
    evidence = _load(root / "evidence.json")
    if metadata.get("artifact") != ARTIFACT_NAME:
        raise EvidenceError("artifact name mismatch")
    if metadata.get("repository") != args.repository:
        raise EvidenceError("repository mismatch")
    if metadata.get("workflow") != args.workflow:
        raise EvidenceError("workflow mismatch")
    if metadata.get("producer_sha") != args.expected_sha:
        raise EvidenceError("producer SHA mismatch")
    if metadata.get("elasticsearch_version") != ELASTICSEARCH_VERSION:
        raise EvidenceError("metadata Elasticsearch version mismatch")
    if metadata.get("integration_tests_executed") is not True:
        raise EvidenceError("integration tests were not explicitly executed")
    if metadata.get("skipped_tests_accepted") is not False:
        raise EvidenceError("skipped tests cannot be accepted as certification")
    if evidence.get("producer_sha") != args.expected_sha or evidence.get("status") != "pass":
        raise EvidenceError("evidence envelope is not an exact-SHA pass")
    _validate(root, args.expected_sha)
    print(f"Team 2 Sprint 4 evidence independently verified for {args.expected_sha}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)

    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--directory", required=True)
    generate_parser.add_argument("--repository", required=True)
    generate_parser.add_argument("--workflow", required=True)
    generate_parser.add_argument("--run-id", required=True)
    generate_parser.add_argument("--job-id", required=True)
    generate_parser.add_argument("--event", required=True)
    generate_parser.set_defaults(func=generate)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--directory", required=True)
    verify_parser.add_argument("--repository", required=True)
    verify_parser.add_argument("--workflow", required=True)
    verify_parser.add_argument("--expected-sha", required=True)
    verify_parser.set_defaults(func=verify)
    return result


def main() -> int:
    args = parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
