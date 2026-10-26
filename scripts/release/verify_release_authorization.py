#!/usr/bin/env python3
"""Validate the single exact-SHA authorization consumed by publication."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.release.release_metadata import REPOSITORY, terminal_migration

TAG = re.compile(r"^v\d+\.\d+\.\d+(?:(?:-beta\.\d+)|(?:-rc\.\d+))?$")


def validate(document: dict, *, repository: str, sha: str, tag: str, run_id: str) -> None:
    if not TAG.fullmatch(tag):
        raise ValueError("tag must be a production, beta, or RC semantic version")
    required = {
        "repository": repository,
        "producer_sha": sha,
        "workflow_run_id": run_id,
        "terminal_migration": terminal_migration(),
        "security_gate": "PASS",
        "beta_certification": "PASS",
        "release_authorized": True,
    }
    for key, expected in required.items():
        if document.get(key) != expected:
            raise ValueError(f"authorization {key} must equal {expected!r}")
    platform = document.get("supported_platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("a certified supported platform is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.artifact.read_text()),
        repository=args.repository,
        sha=args.sha,
        tag=args.tag,
        run_id=args.workflow_run_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
