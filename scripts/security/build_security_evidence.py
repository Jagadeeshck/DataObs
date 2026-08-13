#!/usr/bin/env python3
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

FILES = [
    "docs/development/team-0-security-compliance-evidence-v1-audit.md",
    "docs/security/security-controls.yaml",
    "docs/security/security-evidence-registry.yaml",
    "docs/security/threat-model-registry.yaml",
    "docs/security/trust-boundaries.yaml",
    "route-security-report.json",
    "secret-handling-report.json",
    "audit-safety-report.json",
    "workflow-security-report.json",
    "security-posture-report.json",
    "security-release-gate.json",
    "security-evidence-verification.json",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, default=Path("team-0-security-compliance-evidence-v1-evidence"))
    p.add_argument("--sha", required=True)
    a = p.parse_args()
    a.directory.mkdir(exist_ok=True)
    items = []
    for rel in FILES:
        src = Path(rel) if Path(rel).exists() else a.directory / Path(rel).name
        if src.exists():
            items.append(
                {
                    "path": str(src.relative_to(a.directory) if src.is_relative_to(a.directory) else src),
                    "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                }
            )
    terminal = subprocess.check_output(["python", "scripts/release/current_terminal_migration.py"], text=True).strip()
    manifest = {
        "schema_version": "1.0",
        "artifact": "team-0-security-compliance-evidence-v1-evidence",
        "repository": "Jagadeeshck/DataObs",
        "exact_sha": a.sha,
        "terminal_migration": terminal,
        "environment_class": "local",
        "tool_versions": {"python": platform.python_version()},
        "files": items,
    }
    (a.directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
