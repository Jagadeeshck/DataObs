from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .models import EffectivenessClass, RemediationEpisode, VerificationStatus


@dataclass(frozen=True)
class EffectivenessSummary:
    attempt_count: int
    verification_eligible_count: int
    verified_effect_count: int
    verification_coverage: float
    verified_effect_rate: float | None
    time_to_effect_sample_count: int
    median_time_to_verified_effect_ms: float | None


def summarize(episodes: Iterable[RemediationEpisode]) -> EffectivenessSummary:
    items = tuple(episodes)
    for attribute in ("tenant_id", "environment", "effectiveness_definition_version"):
        if len({getattr(item, attribute) for item in items}) > 1:
            raise ValueError(f"mixed {attribute} effectiveness summary is prohibited")
    eligible = tuple(e for e in items if e.verification_status != VerificationStatus.UNAVAILABLE)
    verified = sum(e.effectiveness_class == EffectivenessClass.VERIFIED_EFFECTIVE for e in eligible)
    timings = [
        e.time_to_verified_effect_ms
        for e in items
        if e.effectiveness_class == EffectivenessClass.VERIFIED_EFFECTIVE and e.time_to_verified_effect_ms is not None
    ]
    return EffectivenessSummary(
        attempt_count=len(items),
        verification_eligible_count=len(eligible),
        verified_effect_count=verified,
        verification_coverage=len(eligible) / len(items) if items else 0,
        verified_effect_rate=verified / len(eligible) if eligible else None,
        time_to_effect_sample_count=len(timings),
        median_time_to_verified_effect_ms=median(timings) if timings else None,
    )
