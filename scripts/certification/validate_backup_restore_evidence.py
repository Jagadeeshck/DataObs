#!/usr/bin/env python3
"""Fail closed before wrapping destructive backup/restore evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.certification.provenance import certification_commit_sha  # noqa: E402
from scripts.release.release_metadata import ELASTICSEARCH_VERSION, terminal_migration  # noqa: E402


def validate(report_path: Path, junit_path: Path) -> None:
    if not junit_path.is_file() or junit_path.stat().st_size == 0:
        raise ValueError(f"missing or empty JUnit report: {junit_path}")
    if not report_path.is_file() or report_path.stat().st_size == 0:
        raise ValueError(f"missing or empty destructive restore report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    root = ET.parse(junit_path).getroot()
    cases = root.findall(".//testcase")
    if root.tag not in {"testsuite", "testsuites"} or len(cases) != 1:
        raise ValueError("recovery JUnit must contain exactly one executed destructive test")
    case = cases[0]
    if case.get("name") != "test_beta_backup_restore_exact_state_and_tenant_isolation" or any(
        case.find(tag) is not None for tag in ("skipped", "failure", "error")
    ):
        raise ValueError("recovery JUnit contains skipped, failed, or unexpected test")
    for suite in root.iter("testsuite"):
        if any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
            raise ValueError("recovery JUnit suite is not passing")
    expected = {
        "commit_sha": certification_commit_sha(),
        "snapshot_result": "pass",
        "destructive_deletion_result": "pass",
        "restore_result": "pass",
        "integrity_verification": "pass",
        "recovery_result": "pass",
        "status": "pass",
        "elasticsearch_version": ELASTICSEARCH_VERSION,
        "terminal_migration": terminal_migration(),
        "tenant_isolation": "pass",
        "redaction_status": "pass",
    }
    mismatches = [
        f"{key}={report.get(key)!r}, expected {value!r}" for key, value in expected.items() if report.get(key) != value
    ]
    if mismatches:
        raise ValueError("invalid destructive restore report: " + "; ".join(mismatches))
    for key in ("snapshot_repository", "snapshot"):
        if not isinstance(report.get(key), str) or not report[key].strip():
            raise ValueError(f"missing recovery field: {key}")
    start, end = (datetime.fromisoformat(report[key]) for key in ("started_at", "completed_at"))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError("invalid recovery timing")
    for key in ("backup_duration_seconds", "restore_duration_seconds", "duration_seconds"):
        duration = report.get(key)
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration <= 0
        ):
            raise ValueError(f"invalid recovery duration: {key}")
    if not report.get("resources"):
        raise ValueError("invalid destructive restore report: resources must be nonempty")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--junit", required=True, type=Path)
    args = parser.parse_args()
    validate(args.report, args.junit)
    print("backup/restore evidence inputs validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
