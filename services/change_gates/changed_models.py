from __future__ import annotations

from hashlib import sha256
from typing import Any

from integrations.dbt.contracts import DbtArtifactEnvelope
from integrations.dbt.normalizer import parse_manifest as parse_canonical_manifest
from integrations.dbt.safety import ArtifactLimits


def parse_manifest(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compatibility wrapper; parsing and safety policy live in integrations.dbt."""
    normalized = parse_canonical_manifest(
        document,
        DbtArtifactEnvelope("change-gate", "change-gate", "change-gate", "unknown", "manifest", "", ""),
        ArtifactLimits(max_resources=2_000, max_columns=1_000, max_bytes=10_000_000),
    )
    return {
        item["unique_id"]: {
            **item,
            "package_name": item["package"],
            "depends_on": item["dependencies"],
            "columns": {column["name"]: column for column in item["columns"]},
            "fingerprint": item["definition_fingerprint"],
            "code_fingerprint": next(
                (
                    (node.get("checksum") or {}).get("checksum")
                    for key, node in (document.get("nodes") or {}).items()
                    if key == item["unique_id"]
                ),
                None,
            ),
        }
        for item in normalized.resources
        if item["resource_type"] == "model"
    }


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
            kind = (
                "unchanged"
                if before[unique_id]["fingerprint"] == after[unique_id]["fingerprint"]
                and before[unique_id]["code_fingerprint"] == after[unique_id]["code_fingerprint"]
                else "modified"
            )
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
