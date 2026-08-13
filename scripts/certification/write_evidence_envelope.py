#!/usr/bin/env python3
"""Write the single, versioned certification evidence envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.release.release_metadata import ELASTICSEARCH_VERSION, terminal_migration  # noqa: E402

SHA = re.compile(r"^[0-9a-f]{40}$")
SECRET = re.compile(
    r"(?i)(authorization\s*:|bearer\s+[a-z0-9._-]+|https://[^\s/]+/(?:hooks|webhook)/|token|client_secret|private_key)"
)


def build_envelope(args: argparse.Namespace) -> dict[str, object]:
    if not SHA.fullmatch(args.producer_sha):
        raise ValueError("producer SHA must be an exact lowercase 40-character SHA")
    summaries = [{"category": item, "status": "pass"} for item in args.test_category]
    summaries.extend(
        {"category": category, "status": status}
        for category, status in (item.split("=", 1) for item in args.test_result)
    )
    categories = [item["category"] for item in summaries]
    if len(categories) != len(set(categories)):
        raise ValueError("test categories must be unique")
    inventory = []
    for item in args.supporting_file:
        path = Path(item)
        inventory.append({"path": path.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    value: dict[str, object] = {
        "schema_version": "1.0",
        "repository": args.repository,
        "producer_sha": args.producer_sha,
        "workflow_file": args.workflow_file,
        "workflow_run_id": str(args.workflow_run_id),
        "workflow_run_attempt": str(args.workflow_run_attempt),
        "event": args.event,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elasticsearch_version": ELASTICSEARCH_VERSION,
        "terminal_migration": terminal_migration(),
        "tool_versions": dict(item.split("=", 1) for item in args.tool_version),
        "test_summaries": summaries,
        "artifact_inventory": inventory,
        "redaction_status": "pass",
        "status": args.status,
    }
    encoded = json.dumps(value, sort_keys=True)
    if SECRET.search(encoded):
        raise ValueError("evidence envelope failed redaction scan")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--producer-sha", required=True)
    parser.add_argument("--workflow-file", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-run-attempt", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--status", choices=("pass", "fail", "not_run", "blocked_external"), required=True)
    parser.add_argument("--test-category", action="append", default=[], help="executed, passing category")
    parser.add_argument(
        "--test-result",
        action="append",
        default=[],
        metavar="CATEGORY=STATUS",
        help="category result; STATUS is pass, fail, not_run, or blocked_external",
    )
    parser.add_argument("--tool-version", action="append", default=[])
    parser.add_argument("--supporting-file", action="append", default=[])
    args = parser.parse_args()
    allowed = {"pass", "fail", "not_run", "blocked_external"}
    for result in args.test_result:
        if "=" not in result or result.split("=", 1)[1] not in allowed:
            parser.error("--test-result must be CATEGORY=pass|fail|not_run|blocked_external")
    if not args.test_category and not args.test_result:
        parser.error("at least one test category/result is required")
    value = build_envelope(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
