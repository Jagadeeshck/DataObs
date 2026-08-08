from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ActionTarget:
    target_type: str
    target_id: str
    revision: str


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


@dataclass(frozen=True)
class TargetResolution:
    status: str
    target: ActionTarget | None
    source_finding_reference: str | None
    resolution_confidence: str
    candidate_count: int
    truncated: bool
    missing_inputs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    candidates: tuple[ActionTarget, ...] = ()


class ActionTargetResolver(Protocol):
    def resolve(self, *, tenant_id: str, environment: str, incident_id: str, action_type: str) -> TargetResolution: ...
    def reload(self, *, tenant_id: str, environment: str, target: ActionTarget) -> ActionTarget: ...


class IncidentFindingReader(Protocol):
    def relevant_finding_references(
        self, tenant_id: str, environment: str, incident_id: str, limit: int
    ) -> Sequence[str]: ...


class FindingReader(Protocol):
    def get_finding(self, tenant_id: str, environment: str, finding_reference: str) -> dict[str, Any] | None: ...


class TargetOwnerReader(Protocol):
    def get_target(self, tenant_id: str, environment: str, target_type: str, target_id: str) -> ActionTarget | None: ...


class BoundedActionTargetResolver:
    """Resolve only finding-backed identities and reload revisions from capability owners."""

    FIELDS = {
        "rerun_scan": ("scanner", "scanner_id"),
        "freshness_recheck": ("monitor", "monitor_id"),
        "connection_test": ("integration", "integration_id"),
    }

    def __init__(
        self,
        incidents: IncidentFindingReader,
        findings: FindingReader,
        owners: TargetOwnerReader,
        *,
        max_findings: int = 50,
        max_candidates: int = 10,
        max_repository_calls: int = 75,
        max_elapsed_seconds: float = 2.0,
    ) -> None:
        if min(max_findings, max_candidates, max_repository_calls) < 1 or max_elapsed_seconds <= 0:
            raise ValueError("target resolution bounds must be positive")
        self.incidents, self.findings, self.owners = incidents, findings, owners
        self.max_findings, self.max_candidates = max_findings, max_candidates
        self.max_repository_calls, self.max_elapsed_seconds = max_repository_calls, max_elapsed_seconds

    def resolve(self, *, tenant_id: str, environment: str, incident_id: str, action_type: str) -> TargetResolution:
        if action_type not in self.FIELDS:
            return self._unavailable(("unsupported_action",), ("action_type",))
        target_type, identity_field = self.FIELDS[action_type]
        started, calls = monotonic(), 1
        references = tuple(
            self.incidents.relevant_finding_references(tenant_id, environment, incident_id, self.max_findings + 1)
        )
        truncated = len(references) > self.max_findings
        candidates: dict[str, tuple[ActionTarget, str]] = {}
        for reference in references[: self.max_findings]:
            if calls + 2 > self.max_repository_calls or monotonic() - started >= self.max_elapsed_seconds:
                truncated = True
                break
            calls += 1
            finding = self.findings.get_finding(tenant_id, environment, reference)
            target_id = finding.get(identity_field) if finding else None
            if not isinstance(target_id, str) or not target_id:
                continue
            calls += 1
            current = self.owners.get_target(tenant_id, environment, target_type, target_id)
            if current is not None:
                candidates[current.target_id] = (current, reference[:200])
            if len(candidates) >= self.max_candidates:
                truncated = truncated or len(references) > 0
                break
        ordered = tuple(value for value, _ in sorted(candidates.values(), key=lambda item: item[0].target_id))
        if len(ordered) == 1 and not truncated:
            target = ordered[0]
            return TargetResolution(
                "resolved",
                target,
                candidates[target.target_id][1],
                "authoritative",
                1,
                False,
                (),
                ("finding_identity_resolved",),
                ordered,
            )
        if ordered:
            return TargetResolution(
                "selection_required",
                None,
                None,
                "authoritative",
                len(ordered),
                truncated,
                (),
                ("multiple_authoritative_targets",),
                ordered,
            )
        return self._unavailable(("no_authoritative_target",), ("finding_target_identity",), truncated)

    def reload(self, *, tenant_id: str, environment: str, target: ActionTarget) -> ActionTarget:
        current = self.owners.get_target(tenant_id, environment, target.target_type, target.target_id)
        if current is None:
            raise LookupError("authoritative target unavailable")
        return current

    @staticmethod
    def _unavailable(reasons: tuple[str, ...], missing: tuple[str, ...], truncated: bool = False) -> TargetResolution:
        return TargetResolution("unavailable", None, None, "none", 0, truncated, missing, reasons)


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
    """Compatibility helper for already-bounded snapshots; production uses BoundedActionTargetResolver."""
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
            target_type,
            target_id[:200],
            revision[:120],
            str(item.get("source", "incident_evidence"))[:80],
            str(item["asset_id"])[:200] if item.get("asset_id") else None,
            str(item["scan_policy_id"])[:200] if item.get("scan_policy_id") else None,
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
