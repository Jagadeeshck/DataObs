#!/usr/bin/env python3
<<<<<<< HEAD
"""Static, offline validation of the Beta certification manifest."""
=======
"""Fail-closed validation of the Beta certification contract."""
>>>>>>> origin/main

from __future__ import annotations

import argparse
<<<<<<< HEAD
import copy
=======
import json
import re
>>>>>>> origin/main
import sys
from pathlib import Path
from typing import Any

<<<<<<< HEAD
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.release.release_metadata import (  # noqa: E402
    ELASTICSEARCH_VERSION,
    REPOSITORY,
    terminal_migration,
)

SUPPORTED_SCHEMAS = {"1.0"}
EXACT_EVENTS = {"workflow_dispatch", "push"}


class WorkflowLoader(yaml.SafeLoader):
    """Do not let YAML 1.1 coerce the GitHub Actions `on` key to True."""


WorkflowLoader.yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
for first, resolvers in list(WorkflowLoader.yaml_implicit_resolvers.items()):
    WorkflowLoader.yaml_implicit_resolvers[first] = [
        item for item in resolvers if item[0] != "tag:yaml.org,2002:bool"
    ]


def _artifacts(workflow: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for job in (workflow.get("jobs") or {}).values():
        delegated_name = (job.get("with") or {}).get("artifact-name")
        if isinstance(delegated_name, str):
            result.add(delegated_name)
        for step in job.get("steps", []):
            if "actions/upload-artifact" in str(step.get("uses", "")):
                name = (step.get("with") or {}).get("name")
                if isinstance(name, str):
                    result.add(name)
    return result


def validate_manifest(path: Path, root: Path = ROOT) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("repository") != REPOSITORY:
        errors.append("repository identity is incorrect")
    if data.get("target_elasticsearch_version") != ELASTICSEARCH_VERSION:
        errors.append("target Elasticsearch version is incorrect")
    if data.get("terminal_migration") != terminal_migration():
        errors.append("terminal migration differs from executable registry")
    seen: set[tuple[str, str]] = set()
    for entry in data.get("capabilities", []):
        cid = str(entry.get("capability_id", "<missing>"))
        workflow_name, artifact = entry.get("workflow"), entry.get("artifact")
        pair = (str(workflow_name), str(artifact))
        if pair in seen:
            errors.append(f"{cid}: duplicate workflow/artifact pair")
        seen.add(pair)
        if not entry.get("required_test_categories"):
            errors.append(f"{cid}: required test categories are empty")
        if str(entry.get("evidence_schema_version")) not in SUPPORTED_SCHEMAS:
            errors.append(f"{cid}: unsupported evidence schema")
        if entry.get("expected_elasticsearch_version") != ELASTICSEARCH_VERSION:
            errors.append(f"{cid}: Elasticsearch version is incorrect")
        mandatory = entry.get("mandatory_for_beta") is True
        if mandatory and entry.get("optional_reason"):
            errors.append(f"{cid}: mandatory capability contains optional exclusion text")
        if not mandatory and not entry.get("optional_reason"):
            errors.append(f"{cid}: optional capability requires a reason")
        events = set(entry.get("accepted_events") or [])
        if not events or not events <= EXACT_EVENTS:
            errors.append(f"{cid}: accepted events do not support exact-commit certification")
        workflow_path = root / ".github/workflows" / str(workflow_name)
        if not workflow_path.is_file():
            errors.append(f"{cid}: workflow does not exist: {workflow_name}")
            continue
        workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=WorkflowLoader)
        triggers = workflow.get("on") or {}
        trigger_names = {triggers} if isinstance(triggers, str) else set(triggers)
        if not events <= trigger_names:
            errors.append(f"{cid}: workflow does not declare every accepted event")
        if artifact not in _artifacts(workflow):
            errors.append(f"{cid}: artifact name is not uploaded by workflow")
        declared_team = entry.get("owning_team")
        if declared_team not in {f"Team {number}" for number in range(1, 7)}:
            errors.append(f"{cid}: invalid owning team")
        if not cid.startswith(f"team{str(declared_team).split()[-1]}."):
            errors.append(f"{cid}: capability ownership does not match capability id")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/release/beta-1-certification-manifest.yaml")
    args = parser.parse_args()
    errors = validate_manifest(args.manifest)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated {args.manifest}")
    return 0
=======
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
>>>>>>> origin/main


if __name__ == "__main__":
    raise SystemExit(main())
