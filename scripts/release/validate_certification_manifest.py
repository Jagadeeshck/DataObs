#!/usr/bin/env python3
"""Fail-closed validation of the Beta certification contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.current_terminal_migration import migration_report

TEAMS = {f"Team {n}" for n in range(7)}
REQUIRED_CATEGORIES = {
    "platform_deployment_packaging",
    "identity_tenant_security",
    "kafka_stream_observer",
    "connector_schema_360",
    "pathway_intelligence_explorer",
    "data_quality_console",
    "job_run_observability",
    "lineage_explorer",
    "incident_workbench",
    "console_cross_team_integration",
    "backup_restore",
    "upgrade_rollback",
    "image_sbom_vulnerability_scan",
}


def validate(path: Path, root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    data = yaml.safe_load(path.read_text())
    errors = []
    report = migration_report()
    for key, value in {
        "schema_version": "1.1",
        "release": "beta-1",
        "release_candidate": "rc1",
        "repository": "Jagadeeshck/DataObs",
        "target_elasticsearch_version": "9.4.2",
    }.items():
        if str(data.get(key)) != value:
            errors.append(f"{key} must be {value}")
    if data.get("terminal_migration") != report["terminal_migration"]:
        errors.append("terminal migration does not match registry")
    seen_ids = set()
    seen_pairs = set()
    covered = set()
    for entry in data.get("capabilities", []):
        cid = entry.get("capability_id")
        pair = (entry.get("workflow"), entry.get("artifact"))
        if cid in seen_ids:
            errors.append(f"duplicate capability ID: {cid}")
        if pair in seen_pairs:
            errors.append(f"duplicate workflow/artifact pair: {pair}")
        seen_ids.add(cid)
        seen_pairs.add(pair)
        if entry.get("owning_team") not in TEAMS:
            errors.append(f"invalid owning team for {cid}")
        if not entry.get("artifact"):
            errors.append(f"missing artifact for {cid}")
        categories = set(entry.get("required_test_categories") or [])
        covered |= categories
        if entry.get("mandatory_for_beta") and not categories:
            errors.append(f"mandatory capability {cid} has no test categories")
        if not entry.get("mandatory_for_beta") and not (entry.get("exclusion") or entry.get("reason_for_inclusion")):
            errors.append(f"excluded capability {cid} has no reason")
        workflow = root / ".github/workflows" / str(entry.get("workflow"))
        if not workflow.is_file():
            errors.append(f"workflow does not exist: {entry.get('workflow')}")
            continue
        source = workflow.read_text()
        if "workflow_dispatch" not in source or "target_sha:" not in source:
            errors.append(f"workflow lacks exact-SHA dispatch: {entry.get('workflow')}")
        if str(entry.get("artifact")) not in source:
            errors.append(f"workflow does not upload artifact {entry.get('artifact')}")
        if "current_terminal_migration.py" not in source:
            errors.append(f"workflow does not derive terminal migration: {entry.get('workflow')}")
        if re.search(r"^\s*uses:\s*\./\.github/workflows/", source, re.M) and "upload-artifact" not in source:
            errors.append(f"reusable workflow is not an evidence producer: {entry.get('workflow')}")
    missing = sorted(REQUIRED_CATEGORIES - covered)
    if missing:
        errors.append("mandatory Beta groups missing: " + ", ".join(missing))
    return {
        "schema_version": "1.1",
        "manifest": str(path),
        "terminal_migration": report["terminal_migration"],
        "migration_count": report["migration_count"],
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = validate(a.manifest)
    out = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(out, end="")
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(out)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
