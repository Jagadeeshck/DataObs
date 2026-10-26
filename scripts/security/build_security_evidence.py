#!/usr/bin/env python3
"""Build an immutable, exact-SHA bundle from explicit runtime reports."""

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_REPORTS = (
    "route-security-report.json",
    "secret-handling-report.json",
    "audit-safety-report.json",
    "workflow-security-report.json",
    "security-posture-report.json",
    "security-release-gate.json",
)


def exact_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise argparse.ArgumentTypeError("SHA must be exactly 40 lowercase hexadecimal characters")
    return value


def build(source: Path, destination: Path, sha: str, provenance: dict[str, str]) -> dict:
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination must differ")
    missing = [name for name in REQUIRED_REPORTS if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError("missing mandatory current-run reports: " + ", ".join(missing))
    destination.mkdir(parents=True, exist_ok=False)
    inventory = []
    for name in REQUIRED_REPORTS:
        src = source / name
        report = json.loads(src.read_text())
        report_sha = report.get("sha") or report.get("exact_sha")
        if report_sha != sha:
            raise ValueError(f"{name}: report SHA {report_sha!r} does not match {sha}")
        target = destination / name
        shutil.copyfile(src, target)
        inventory.append({"path": name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    terminal = subprocess.check_output(["python", "scripts/release/current_terminal_migration.py"], text=True).strip()
    manifest = {
        "schema_version": "1.1",
        "artifact": "team-0-security-compliance-evidence-v1-evidence",
        "repository": "Jagadeeshck/DataObs",
        "exact_sha": sha,
        "terminal_migration": terminal,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment_class": "github_ci_integrity_check" if provenance["workflow_run_id"] else "local_integrity_check",
        "hosted_product_validation": False,
        "independently_verified": False,
        "workflow": provenance["workflow"],
        "workflow_run_id": provenance["workflow_run_id"],
        "run_attempt": provenance["run_attempt"],
        "event": provenance["event"],
        "tool_versions": {"python": platform.python_version()},
        "files": inventory,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--sha", type=exact_sha, required=True)
    parser.add_argument("--workflow", default="local")
    parser.add_argument("--workflow-run-id", default="")
    parser.add_argument("--run-attempt", default="")
    parser.add_argument("--event", default="local")
    args = parser.parse_args()
    build(args.source_directory, args.directory, args.sha, vars(args))


if __name__ == "__main__":
    main()
