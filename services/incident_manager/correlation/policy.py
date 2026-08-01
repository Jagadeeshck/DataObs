from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CorrelationPolicy:
    name: str = "dataobs-incident-correlation"
    version: str = "v1"
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "same_asset": 0.30,
            "same_primary_resource": 0.20,
            "same_monitor": 0.15,
            "same_trace": 0.30,
            "same_run": 0.25,
            "same_job": 0.25,
            "same_source": 0.10,
            "same_data_product": 0.20,
            "same_business_service": 0.15,
            "lineage_adjacency": 0.20,
            "temporal_proximity": 0.15,
            "compatible_finding_type": 0.10,
        }
    )
    correlation_window_seconds: int = 3600
    minimum_score: float = 0.35
    minimum_evidence_coverage: float = 0.25
    maximum_candidates: int = 100
    maximum_members: int = 50
    maximum_features: int = 24

    @property
    def canonical_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


V1_POLICY = CorrelationPolicy()
