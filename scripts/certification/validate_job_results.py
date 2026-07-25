#!/usr/bin/env python3
"""Validate focused certification job conclusions without masking required skips."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

ALL_JOBS = {
    "contracts",
    "migrations-incidents",
    "postgres",
    "kafka",
    "openlineage-product",
    "browser",
    "security",
}
REQUIRED_JOBS = {
    "all": ALL_JOBS,
    "postgres": {"contracts", "postgres"},
    "kafka": {"contracts", "kafka"},
    "openlineage": {"contracts", "openlineage-product"},
    "product": {"contracts", "openlineage-product"},
    "browser": {"contracts", "browser"},
    "security": {"contracts", "security"},
}


def validate(scope: str, results: Mapping[str, str]) -> dict[str, object]:
    if scope not in REQUIRED_JOBS:
        return {
            "scope": scope,
            "partial": True,
            "required_jobs": [],
            "expected_skipped_jobs": [],
            "errors": [f"unsupported scope: {scope}"],
        }
    required = REQUIRED_JOBS[scope]
    expected_skipped = ALL_JOBS - required
    errors = []
    for job in sorted(required):
        if results.get(job) != "success":
            errors.append(f"required job {job} concluded {results.get(job, 'missing')}, expected success")
    for job in sorted(expected_skipped):
        if results.get(job) != "skipped":
            errors.append(f"unselected job {job} concluded {results.get(job, 'missing')}, expected skipped")
    unknown = set(results) - ALL_JOBS
    errors.extend(f"unexpected job: {job}" for job in sorted(unknown))
    return {
        "scope": scope,
        "partial": scope != "all",
        "required_jobs": sorted(required),
        "expected_skipped_jobs": sorted(expected_skipped),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scope", choices=sorted(REQUIRED_JOBS))
    parser.add_argument("results", help="JSON object or path to a JSON object")
    args = parser.parse_args()
    candidate = Path(args.results)
    raw = candidate.read_text() if candidate.is_file() else args.results
    summary = validate(args.scope, json.loads(raw))
    print(json.dumps(summary, sort_keys=True, indent=2))
    return bool(summary["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
