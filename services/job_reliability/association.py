"""Deterministic actual-run to expected-run association."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from packages.domain_model.job_run import ExpectedRun


@dataclass(frozen=True)
class Association:
    expected_run_id: str | None
    confidence: float
    reason_codes: tuple[str, ...]


def associate_actual_run(
    *,
    tenant_id: str,
    environment: str,
    job_id: str,
    run_id: str,
    started_at: datetime | None,
    expected_runs: Iterable[ExpectedRun],
    scheduled_at: datetime | None = None,
    provider_facets: dict[str, Any] | None = None,
) -> Association:
    """Prefer exact provider schedule evidence, then the nearest eligible window."""
    candidates = [
        value
        for value in expected_runs
        if (value.tenant_id, value.environment, value.job_id) == (tenant_id, environment, job_id)
        and value.actual_run_id in (None, run_id)
    ]
    already = [value for value in candidates if value.actual_run_id == run_id]
    if already:
        return Association(already[0].expected_run_id, 1.0, ("existing_association",))
    if scheduled_at is not None:
        exact = [value for value in candidates if value.scheduled_at == scheduled_at]
        if len(exact) == 1:
            return Association(exact[0].expected_run_id, 1.0, ("exact_scheduled_time",))
    provider_time = (provider_facets or {}).get("scheduled_at")
    if provider_time:
        text = provider_time.isoformat() if isinstance(provider_time, datetime) else str(provider_time)
        exact = [value for value in candidates if value.scheduled_at.isoformat() == text]
        if len(exact) == 1:
            return Association(exact[0].expected_run_id, 0.95, ("provider_scheduled_time",))
    if started_at is None:
        return Association(None, 0.0, ("actual_start_missing",))
    eligible = [value for value in candidates if value.permitted_start_at <= started_at <= value.permitted_start_until]
    if not eligible:
        return Association(None, 0.0, ("outside_permitted_window",))
    eligible.sort(
        key=lambda value: (
            abs((started_at - value.scheduled_at).total_seconds()),
            value.scheduled_at,
            value.expected_run_id,
        )
    )
    return Association(eligible[0].expected_run_id, 0.8, ("nearest_permitted_start",))
