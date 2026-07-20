from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ALLOWED_STEP_PREFIXES = ("cases.", "dataobs.", "streams.", "notifications.")
ALLOWED_STEP_TYPES = {"wait", "condition"}
FORBIDDEN_TOKENS = ("kibana.request", "shell", "exec", "sql", "http.request", "credential", "${secret")


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not data.get("id") or not data.get("steps"):
        raise ValueError(f"{path} must define id and steps")
    text = path.read_text()
    if "kibana." in text:
        raise ValueError(f"{path} uses deprecated kibana.* workflow steps; use cases.*")
    lowered = text.lower()
    if any(token in lowered for token in FORBIDDEN_TOKENS):
        raise ValueError(f"{path} contains a forbidden workflow capability")
    for position, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"{path} step {position} must be an object")
        step_type = str(step.get("type") or step.get("action") or "")
        if not step_type or not (step_type in ALLOWED_STEP_TYPES or step_type.startswith(ALLOWED_STEP_PREFIXES)):
            raise ValueError(f"{path} step {position} type {step_type!r} is not allowlisted")
    if "type: alert" in text and "runWorkflowActionRequired: true" not in text:
        raise ValueError(f"{path} alert trigger must document Run Workflow action binding")
    return {"id": data["id"], "checksum": checksum(path), "path": str(path)}


def validate_pack(root: str = "integrations/elastic/workflows/packs/dataobs") -> list[dict[str, Any]]:
    return [validate_workflow(path) for path in sorted(Path(root).glob("*.yaml"))]
