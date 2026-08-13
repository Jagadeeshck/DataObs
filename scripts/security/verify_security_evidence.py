#!/usr/bin/env python3
"""Fail-closed verification for a Team 0 evidence artifact."""

import argparse
import hashlib
import json
import re
from pathlib import Path

REQUIRED_REPORTS = (
    "route-security-report.json",
    "secret-handling-report.json",
    "audit-safety-report.json",
    "workflow-security-report.json",
    "security-posture-report.json",
    "security-release-gate.json",
)


def verify(directory: Path, sha: str, repository: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("target SHA must be exact")
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("exact_sha") != sha or manifest.get("repository") != repository:
        raise ValueError("manifest target mismatch")
    required_provenance = {"workflow", "workflow_run_id", "run_attempt", "event", "generated_at"}
    if not required_provenance <= manifest.keys():
        raise ValueError("manifest provenance is incomplete")
    if manifest.get("independently_verified") is not False:
        raise ValueError("integrity verification is not independent verification")
    entries = {item["path"]: item["sha256"] for item in manifest.get("files", [])}
    if set(entries) != set(REQUIRED_REPORTS):
        raise ValueError("manifest inventory does not contain exactly the required reports")
    for name in REQUIRED_REPORTS:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entries[name]:
            raise ValueError(f"checksum mismatch: {name}")
        report = json.loads(path.read_text())
        if (report.get("sha") or report.get("exact_sha")) != sha:
            raise ValueError(f"mixed producer SHA: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repository", default="Jagadeeshck/DataObs")
    args = parser.parse_args()
    verify(args.directory, args.sha, args.repository)


if __name__ == "__main__":
    main()
