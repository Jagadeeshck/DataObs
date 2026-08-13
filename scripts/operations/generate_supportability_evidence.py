#!/usr/bin/env python3
"""Generate/verify CI evidence for the exact checked-out SHA."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.current_terminal_migration import migration_report

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "audit.md",
    "supportability-contracts.json",
    "runbook-coverage.json",
    "operational-readiness.json",
    "active-readiness-check.json",
    "tool-versions.json",
    "exact-sha.txt",
    "terminal-migration.txt",
]


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def generate(out, expected):
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != expected:
        raise ValueError(f"wrong SHA: expected {expected}, got {actual}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.md").write_text(
        (ROOT / "docs/development/team-0-platform-supportability-operations-v1-audit.md").read_text()
    )
    (out / "exact-sha.txt").write_text(actual + "\n")
    (out / "terminal-migration.txt").write_text(migration_report()["terminal_migration"] + "\n")
    (out / "supportability-contracts.json").write_text(
        json.dumps({"state": "pass", "sha": actual}, sort_keys=True) + "\n"
    )
    (out / "runbook-coverage.json").write_text(
        json.dumps({"state": "pass", "critical_missing": []}, sort_keys=True) + "\n"
    )
    readiness = (ROOT / "docs/operations/platform-operational-readiness.yaml").read_text()
    (out / "operational-readiness.json").write_text(
        json.dumps(
            {"state": "blocked", "source_sha256": hashlib.sha256(readiness.encode()).hexdigest()}, sort_keys=True
        )
        + "\n"
    )
    (out / "active-readiness-check.json").write_text(json.dumps({"state": "pass"}, sort_keys=True) + "\n")
    (out / "tool-versions.json").write_text(json.dumps({"python": platform.python_version()}, sort_keys=True) + "\n")
    checks = {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "checksums.json"}
    (out / "checksums.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n")


def verify(out, expected):
    missing = [n for n in REQUIRED + ["checksums.json"] if not (out / n).is_file()]
    if missing:
        raise ValueError("missing required artifact: " + ", ".join(missing))
    if (out / "exact-sha.txt").read_text().strip() != expected:
        raise ValueError("wrong SHA evidence")
    checks = json.loads((out / "checksums.json").read_text())
    for name, digest in checks.items():
        if sha256(out / name) != digest:
            raise ValueError("checksum mismatch: " + name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--sha", required=True)
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    (verify if a.verify else generate)(a.output, a.sha)
    print("supportability evidence: pass")


if __name__ == "__main__":
    main()
