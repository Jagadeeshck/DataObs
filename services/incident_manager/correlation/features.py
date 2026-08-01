from __future__ import annotations

from packages.domain_model.incident import Incident

from .contracts import EvidenceState, FeatureResult


def extract_features(left: Incident, right: Incident) -> tuple[FeatureResult, ...]:
    """Compare only bounded, safe projection fields; absent values remain unknown."""
    specs = (
        ("same_asset", set(left.affected_assets), set(right.affected_assets)),
        (
            "same_primary_resource",
            {left.primary_resource} if left.primary_resource else set(),
            {right.primary_resource} if right.primary_resource else set(),
        ),
        ("same_data_product", set(left.data_product_ids), set(right.data_product_ids)),
        ("same_business_service", set(left.business_services), set(right.business_services)),
    )
    results = []
    for name, a, b in specs:
        if not a or not b:
            results.append(FeatureResult(name, EvidenceState.UNAVAILABLE))
        else:
            common = tuple(sorted(a & b)[:5])
            results.append(FeatureResult(name, EvidenceState.MATCHED if common else EvidenceState.NOT_MATCHED, common))
    if left.last_observed_at is None or right.last_observed_at is None:
        results.append(FeatureResult("temporal_proximity", EvidenceState.UNAVAILABLE))
    else:
        results.append(FeatureResult("temporal_proximity", EvidenceState.MATCHED))
    return tuple(results)
