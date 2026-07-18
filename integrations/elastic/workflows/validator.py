from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not data.get("id") or not data.get("steps"):
        raise ValueError(f"{path} must define id and steps")
    text = path.read_text()
    if "kibana." in text:
        raise ValueError(f"{path} uses deprecated kibana.* workflow steps; use cases.*")
    if "type: alert" in text and "runWorkflowActionRequired: true" not in text:
        raise ValueError(f"{path} alert trigger must document Run Workflow action binding")
    return {"id": data["id"], "checksum": checksum(path), "path": str(path)}


def validate_pack(root: str = "integrations/elastic/workflows/packs/dataobs") -> list[dict[str, Any]]:
    return [validate_workflow(path) for path in sorted(Path(root).glob("*.yaml"))]
