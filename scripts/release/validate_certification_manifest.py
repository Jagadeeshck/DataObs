#!/usr/bin/env python3
"""Static, offline validation of the Beta certification manifest."""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

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
TEAM_ZERO = "Team 0"


class WorkflowLoader(yaml.SafeLoader):
    """Do not let YAML 1.1 coerce the GitHub Actions `on` key to True."""


WorkflowLoader.yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
for first, resolvers in list(WorkflowLoader.yaml_implicit_resolvers.items()):
    WorkflowLoader.yaml_implicit_resolvers[first] = [item for item in resolvers if item[0] != "tag:yaml.org,2002:bool"]


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
    aliases = data.get("compatibility_aliases") or {}
    legacy_names: set[str] = set()
    for canonical, contract in aliases.items():
        if not str(canonical).startswith("team-0-"):
            errors.append(f"compatibility alias canonical name is not Team 0: {canonical}")
        names = contract.get("legacy_names", []) if isinstance(contract, dict) else []
        if not names or any(not isinstance(name, str) for name in names):
            errors.append(f"{canonical}: compatibility aliases are empty or invalid")
        if legacy_names.intersection(names):
            errors.append(f"{canonical}: legacy alias is assigned more than once")
        legacy_names.update(names)
        if not set(contract.get("schema_versions", [])) <= SUPPORTED_SCHEMAS:
            errors.append(f"{canonical}: alias supports an unsupported schema")
    seen: set[tuple[str, str]] = set()
    canonical_artifacts: set[str] = set()
    for entry in data.get("capabilities", []):
        cid = str(entry.get("capability_id", "<missing>"))
        workflow_name, artifact = entry.get("workflow"), entry.get("artifact")
        pair = (str(workflow_name), str(artifact))
        if pair in seen:
            errors.append(f"{cid}: duplicate workflow/artifact pair")
        seen.add(pair)
        if str(artifact) in canonical_artifacts:
            errors.append(f"{cid}: canonical artifact satisfies more than one capability")
        canonical_artifacts.add(str(artifact))
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
        if declared_team not in {f"Team {number}" for number in range(0, 6)}:
            errors.append(f"{cid}: invalid owning team")
        if not cid.startswith(f"team{str(declared_team).split()[-1]}."):
            errors.append(f"{cid}: capability ownership does not match capability id")
    return errors


def validate(path: Path, root: Path = ROOT) -> dict[str, Any]:
    """Compatibility API returning the machine-readable validation result."""
    errors = validate_manifest(path, root)
    return {"status": "pass" if not errors else "fail", "errors": errors}


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


if __name__ == "__main__":
    raise SystemExit(main())
