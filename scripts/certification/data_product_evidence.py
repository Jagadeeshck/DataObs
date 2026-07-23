#!/usr/bin/env python3
"""Evidence emitted by the test process that actually executed a scenario."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Sequence


def _commit_sha() -> str:
    return os.getenv("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def write_scenario(
    output_dir: str | Path,
    *,
    filename: str,
    scenario: str,
    elasticsearch_version: str,
    test_names: Sequence[str],
    assertion_summary: Sequence[str],
    redacted_references: Sequence[str],
    started_at: datetime | str,
    completed_at: datetime | str,
    result: str,
) -> Path:
    """Write one real scenario result, rejecting empty/contradictory evidence."""
    if not filename.endswith(".json") or Path(filename).name != filename:
        raise ValueError("scenario filename must be a JSON basename")
    if not scenario or not test_names or not all(test_names) or not assertion_summary or not all(assertion_summary):
        raise ValueError("scenario, test_names and assertion_summary must be non-empty")
    if result not in {"passed", "failed"}:
        raise ValueError("result must be passed or failed")
    start = started_at.isoformat() if isinstance(started_at, datetime) else started_at
    complete = completed_at.isoformat() if isinstance(completed_at, datetime) else completed_at
    if datetime.fromisoformat(start.replace("Z", "+00:00")) > datetime.fromisoformat(complete.replace("Z", "+00:00")):
        raise ValueError("started_at must not be after completed_at")
    document = {
        "schema_version": "1.0",
        "scenario": scenario,
        "commit_sha": _commit_sha(),
        "elasticsearch_version": elasticsearch_version,
        "started_at": start,
        "completed_at": complete,
        "test_names": list(test_names),
        "assertion_summary": list(assertion_summary),
        "redacted_references": list(redacted_references),
        "result": result,
    }
    target = Path(output_dir) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2) + "\n")
    return target
