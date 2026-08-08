from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

MAX_ARTIFACT_BYTES = 10_000_000
MAX_MODELS = 2_000
MAX_COLUMNS = 1_000
FORBIDDEN = {"raw_sql", "compiled_sql", "raw_code", "compiled_code", "env", "credentials", "token", "secret"}


def _reject_unsafe(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN and child not in (None, "", [], {}):
                raise ValueError(f"unsafe dbt field rejected: {path}{key}")
            _reject_unsafe(child, f"{path}{key}.")
    elif isinstance(value, list):
        for child in value:
            _reject_unsafe(child, path)


def parse_manifest(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if len(json.dumps(document, separators=(",", ":")).encode()) > MAX_ARTIFACT_BYTES:
        raise ValueError("dbt artifact exceeds maximum size")
    _reject_unsafe(document)
    nodes = document.get("nodes")
    if not isinstance(nodes, dict):
        raise ValueError("manifest nodes must be an object")
    models = {key: node for key, node in nodes.items() if node.get("resource_type") == "model"}
    if len(models) > MAX_MODELS:
        raise ValueError("manifest exceeds maximum model count")
    result = {}
    for unique_id, node in models.items():
        columns = node.get("columns") or {}
        if not isinstance(columns, dict) or len(columns) > MAX_COLUMNS:
            raise ValueError(f"invalid column metadata for {unique_id}")
        safe = {
            "unique_id": unique_id,
            "name": node.get("name"),
            "resource_type": "model",
            "database": node.get("database"),
            "schema": node.get("schema"),
            "alias": node.get("alias"),
            "package_name": node.get("package_name"),
            "depends_on": sorted(node.get("depends_on", {}).get("nodes", [])),
            "columns": {
                name: {
                    "data_type": col.get("data_type"),
                    "nullable": col.get("nullable", True),
                    "constraints": col.get("constraints", []),
                }
                for name, col in sorted(columns.items())
            },
            "materialization": (node.get("config") or {}).get("materialized"),
            "tags": sorted(node.get("tags") or []),
            "meta": {k: v for k, v in (node.get("meta") or {}).items() if k in {"owner", "team", "criticality"}},
            "original_file_path": node.get("original_file_path"),
            "code_fingerprint": (node.get("checksum") or {}).get("checksum") or node.get("compiled_code_fingerprint"),
        }
        safe["fingerprint"] = sha256(json.dumps(safe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        result[unique_id] = safe
    return result


def detect_changes(base: dict[str, Any], head: dict[str, Any], include_unchanged: bool = False) -> list[dict[str, Any]]:
    before, after = parse_manifest(base), parse_manifest(head)
    changes = []
    removed, added = set(before) - set(after), set(after) - set(before)
    rename_to: dict[str, str] = {}
    for old in sorted(removed):
        candidates = [
            new
            for new in added
            if before[old]["code_fingerprint"] and before[old]["code_fingerprint"] == after[new]["code_fingerprint"]
        ]
        if len(candidates) == 1:
            rename_to[old] = candidates[0]
    for unique_id in sorted(set(before) | set(after)):
        if unique_id in before and unique_id in after:
            kind = "unchanged" if before[unique_id]["fingerprint"] == after[unique_id]["fingerprint"] else "modified"
        elif unique_id in rename_to:
            kind = "renamed_candidate"
        elif unique_id in rename_to.values():
            continue
        else:
            kind = "removed" if unique_id in before else "added"
        if kind != "unchanged" or include_unchanged:
            changes.append(
                {
                    "unique_id": unique_id,
                    "change_type": kind,
                    "base": before.get(unique_id),
                    "head": after.get(rename_to.get(unique_id, unique_id)),
                    "renamed_to": rename_to.get(unique_id),
                }
            )
    return changes
