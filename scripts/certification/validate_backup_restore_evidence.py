#!/usr/bin/env python3
"""Fail closed before wrapping destructive backup/restore evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.release.release_metadata import ELASTICSEARCH_VERSION, terminal_migration


def validate(report_path: Path, junit_path: Path) -> None:
    if not junit_path.is_file() or junit_path.stat().st_size == 0:
        raise ValueError(f"missing or empty JUnit report: {junit_path}")
    if not report_path.is_file() or report_path.stat().st_size == 0:
        raise ValueError(f"missing or empty destructive restore report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = {
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
