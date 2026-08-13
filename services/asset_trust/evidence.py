"""Canonical evidence adapters for Asset Trust.

The resolver deliberately depends on small read-only ports.  Provider artifacts are
normalised by their owning service; Asset Trust never recalculates an SLO, monitor,
contract, job, dbt, schema, or lineage result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol

from packages.domain_model.asset_trust import AssetTrustEvidence


@dataclass(frozen=True)
class CanonicalEvidence:
    source: str
    ref: str
    dimension: str
    score: float | None
    confidence: float
    coverage: float
    observed_at: datetime
    state: str = "observed"
    derived_from: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class EvidenceReader(Protocol):
    def read_asset_evidence(self, tenant_id: str, environment: str, asset_id: str) -> Iterable[CanonicalEvidence]: ...


class AssetTrustEvidenceResolver:
    """Fan in canonical projections and apply staleness without changing scores."""

    def __init__(self, readers: Iterable[EvidenceReader], *, staleness_seconds: dict[str, int] | None = None):
        self._readers = tuple(readers)
        self._staleness = staleness_seconds or {}

    def resolve(self, tenant_id: str, environment: str, asset_id: str, *, now: datetime | None = None):
        if not tenant_id or not environment or not asset_id:
            raise ValueError("tenant_id, environment and asset_id are required")
        now = now or datetime.now(timezone.utc)
        result: list[AssetTrustEvidence] = []
        for reader in self._readers:
            for item in reader.read_asset_evidence(tenant_id, environment, asset_id):
                age = max(0, (now - item.observed_at).total_seconds())
                stale = age > self._staleness.get(item.dimension, float("inf"))
                result.append(
                    AssetTrustEvidence(
                        evidence_source=item.source,
                        evidence_ref=item.ref,
                        dimension=item.dimension,
                        score=item.score,
                        confidence=item.confidence,
                        coverage=item.coverage,
                        observed_at=item.observed_at,
                        status="stale" if stale else item.state,
                        derived_from=list(item.derived_from),
                        reason_codes=list(item.reason_codes),
                    )
                )
        return result
