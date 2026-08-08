from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TargetCandidate:
    target_type: str
    target_id: str
    target_revision: str
    source: str
    affected_asset: str | None = None
    scan_policy: str | None = None

    def public(self) -> dict[str, str | None]:
        return {
            "type": self.target_type,
            "id": self.target_id,
            "revision": self.target_revision,
            "source": self.source,
            "affected_asset": self.affected_asset,
            "scan_policy": self.scan_policy,
        }


class TargetSelectionRequired(ValueError):
    def __init__(self, candidates: tuple[TargetCandidate, ...]) -> None:
        super().__init__("target_selection_required")
        self.candidates = candidates


_FIELDS = {
    "rerun_scan": ("scanner", "scanner_id", "scanner_revision"),
    "freshness_recheck": ("monitor", "monitor_id", "monitor_revision"),
    "connection_test": ("integration", "integration_id", "integration_revision"),
}


def resolve_target(
    action_type: str, evidence: list[dict[str, Any]], selected: dict[str, Any] | None = None
) -> TargetCandidate:
    """Resolve and revalidate action targets exclusively from bounded incident evidence."""
    try:
        target_type, id_field, revision_field = _FIELDS[action_type]
    except KeyError as exc:
        raise ValueError("unsupported target resolver") from exc
    unique: dict[tuple[str, str], TargetCandidate] = {}
    for item in evidence[:100]:
        target_id, revision = item.get(id_field), item.get(revision_field)
        if not isinstance(target_id, str) or not target_id or not isinstance(revision, str) or not revision:
            continue
        candidate = TargetCandidate(
            target_type=target_type,
            target_id=target_id[:200],
            target_revision=revision[:120],
            source=str(item.get("source", "incident_evidence"))[:80],
            affected_asset=str(item["asset_id"])[:200] if item.get("asset_id") else None,
            scan_policy=str(item["scan_policy_id"])[:200] if item.get("scan_policy_id") else None,
        )
        unique[(candidate.target_id, candidate.target_revision)] = candidate
    candidates = tuple(sorted(unique.values(), key=lambda value: (value.target_id, value.target_revision))[:25])
    if selected:
        match = next(
            (
                item
                for item in candidates
                if item.target_id == selected.get("target_id")
                and item.target_revision == selected.get("target_revision")
            ),
            None,
        )
        if match:
            return match
        raise ValueError("selected target is not present in authoritative incident evidence")
    if len(candidates) == 1:
        return candidates[0]
    raise TargetSelectionRequired(candidates)
