from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ALLOWED_STEP_TYPES = {"cases.getCase", "cases.addComment", "cases.addTags"}
LEGACY_ALLOWED_STEP_PREFIXES = ("cases.", "dataobs.", "streams.", "notifications.")
LEGACY_ALLOWED_STEP_TYPES = {"wait", "waitForInput", "condition", "elasticsearch.esql"}
DEPRECATED_CASE_ALIASES = {
    "kibana.createCaseDefaultSpace",
    "kibana.getCaseDefaultSpace",
    "kibana.updateCaseDefaultSpace",
    "kibana.addCaseCommentDefaultSpace",
}
FORBIDDEN_STEP_TYPES = {
    "kibana.request",
    "shell",
    "script",
    "exec",
    "http",
    "http.request",
    "cases.deleteCases",
    "cases.pushCases",
}


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_steps(value: object, location: str = "steps") -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_steps(item, f"{location}[{index}]"))
    elif isinstance(value, dict):
        if "type" in value or "action" in value:
            found.append((location, value))
        for key, nested in value.items():
            if key in {"steps", "branches", "then", "else", "workflow", "sub_workflow", "do"}:
                found.extend(_walk_steps(nested, f"{location}.{key}"))
    return found


def validate_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not data.get("id") or not data.get("steps"):
        raise ValueError(f"{path} must define id and steps")
    text = path.read_text()
    if any(alias in text for alias in DEPRECATED_CASE_ALIASES):
        raise ValueError(f"{path} uses a deprecated Case workflow step; use cases.*")
    lowered = text.lower()
    if "${secret" in lowered or re.search(r"(?<!e)\bsql\b", lowered):
        raise ValueError(f"{path} contains a forbidden workflow capability")
    steps = _walk_steps(data["steps"])
    if not steps:
        raise ValueError(f"{path} must contain typed steps")
    for position, step in steps:
        step_type = str(step.get("type") or step.get("action") or "")
        if step_type == "kibana.request":
            raise ValueError(f"{path} uses a deprecated generic Kibana request step")
        if step_type in FORBIDDEN_STEP_TYPES:
            raise ValueError(f"{path} contains a forbidden workflow capability")
        managed = "definitions" in path.parts
        allowed = step_type in ALLOWED_STEP_TYPES
        legacy_allowed = step_type in LEGACY_ALLOWED_STEP_TYPES or step_type.startswith(LEGACY_ALLOWED_STEP_PREFIXES)
        if not allowed and (managed or not legacy_allowed):
            raise ValueError(f"{path} step {position} type {step_type!r} is not allowlisted")
    if "type: alert" in text and "runWorkflowActionRequired: true" not in text:
        raise ValueError(f"{path} alert trigger must document Run Workflow action binding")
    return {"id": data["id"], "checksum": checksum(path), "path": str(path)}


def validate_pack(root: str = "integrations/elastic/workflows/packs/dataobs") -> list[dict[str, Any]]:
    return [validate_workflow(path) for path in sorted(Path(root).glob("*.yaml"))]


def validate_managed_definitions(root: str = "integrations/elastic/workflows/definitions") -> list[dict[str, Any]]:
    return validate_pack(root)
