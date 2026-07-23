#!/usr/bin/env python3
"""Evidence emitted by the test process that actually executed a scenario."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Sequence

from packages.elastic_store.manifest import data_product_evidence_owners
from scripts.certification.provenance import certification_commit_sha


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
    profile: str | None = None,
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
    start_value = datetime.fromisoformat(start.replace("Z", "+00:00"))
    complete_value = datetime.fromisoformat(complete.replace("Z", "+00:00"))
    if start_value.tzinfo is None or complete_value.tzinfo is None:
        raise ValueError("scenario timestamps must be timezone-aware")
    if start_value > complete_value:
        raise ValueError("started_at must not be after completed_at")
    selected_profile = profile or os.getenv("DATA_PRODUCT_CERTIFICATION_PROFILE")
    if selected_profile:
        owned = {name for names in data_product_evidence_owners(selected_profile).values() for name in names}
        if filename not in owned:
            raise ValueError(f"artifact {filename} is undeclared for profile {selected_profile}")
    document = {
        "schema_version": "1.0",
        "scenario": scenario,
        "commit_sha": certification_commit_sha(),
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


class EvidenceScenarioRecorder:
    """Success-only recorder owned by the pytest scenario that performed assertions."""

    def __init__(self, output_dir: str | Path, filename: str, scenario: str, profile: str, nodeid: str):
        from datetime import timezone

        self.output_dir, self.filename, self.scenario = output_dir, filename, scenario
        self.profile, self.nodeid = profile, nodeid
        self.started_at = datetime.now(timezone.utc)
        self.assertions: list[str] = []
        self.references: list[str] = []

    def assert_that(self, condition: bool, summary: str) -> None:
        assert condition, summary
        self.assertions.append(summary)

    def reference(self, value: str) -> None:
        import hashlib

        self.references.append("sha256:" + hashlib.sha256(value.encode()).hexdigest())

    def passed(self, elasticsearch_version: str) -> Path:
        from datetime import timezone

        return write_scenario(
            self.output_dir,
            filename=self.filename,
            scenario=self.scenario,
            elasticsearch_version=elasticsearch_version,
            test_names=[self.nodeid],
            assertion_summary=self.assertions,
            redacted_references=self.references,
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc),
            result="passed",
            profile=self.profile,
        )
