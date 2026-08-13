#!/usr/bin/env python3
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.current_terminal_migration import migration_report
from scripts.release.validate_migration_graph import validate

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    graph = validate()
    (out / "migration-graph-report.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    reports = {
        name: {"state": "unvalidated", "reason": "no retained executed predecessor evidence"}
        for name in [
            "elasticsearch",
            "kubernetes",
            "helm",
            "runtime",
            "oidc",
            "openapi",
            "configuration",
            "upgrade-readiness",
            "rollback",
            "supportability",
        ]
    }
    reports.update(
        {
            "migration-collision": {"state": "passed" if graph["state"] == "valid" else "failed"},
            "release-gate": {"state": "blocked", "release_decision": "NO_GO"},
        }
    )
    for name, data in reports.items():
        (out / f"{name}-report.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    files = sorted(p for p in out.iterdir() if p.name != "manifest.json")
    manifest = {
        "schema_version": "1.0",
        "exact_sha": sha,
        "terminal_migration": migration_report()["terminal_migration"],
        "audit": "docs/development/team-0-version-upgrade-compatibility-v1-audit.md",
        "tool_versions": {"python": platform.python_version()},
        "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))
    return graph["state"] != "valid"


if __name__ == "__main__":
    raise SystemExit(main())
