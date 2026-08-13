from __future__ import annotations

from datetime import datetime
from typing import Iterable

from packages.domain_model.slo import (
    BurnSignal,
    calculate_burn_rate,
    calculate_error_budget,
    classify_multi_window_burn,
)

from .models import (
    APPROACHING_BREACH_RATIO,
    IncidentObjectiveResult,
    IncidentResponseObjectiveAssignment,
    IncidentResponseObjectiveDefinition,
    IncidentResponseObjectiveEvaluation,
    ObjectiveResultState,
)


def evaluate_incident(
    assignment: IncidentResponseObjectiveAssignment,
    *,
    now: datetime,
    observed_at: datetime | None,
    incident_complete: bool = False,
    historical_breach: bool = False,
    excluded: bool = False,
) -> IncidentObjectiveResult:
    if excluded:
        return _result(assignment, ObjectiveResultState.EXCLUDED, None, False, "excluded", 0, ("approved_exclusion",))
    actual = (observed_at - assignment.effective_at).total_seconds() if observed_at else None
    breached = historical_breach or (
        observed_at > assignment.deadline_at if observed_at else now > assignment.deadline_at
    )
    if observed_at:
        state = ObjectiveResultState.MET_AFTER_BREACH if breached else ObjectiveResultState.MET
        return _result(assignment, state, actual, breached, "available", 1, ())
    if incident_complete:
        return _result(
            assignment,
            ObjectiveResultState.UNAVAILABLE,
            None,
            breached,
            "unavailable",
            0,
            ("completed_without_required_timestamp",),
        )
    if breached:
        return _result(
            assignment, ObjectiveResultState.BREACHED, None, True, "missing", 0, ("deadline_passed_without_timestamp",)
        )
    consumed = (now - assignment.effective_at).total_seconds() / assignment.target_duration_seconds
    state = (
        ObjectiveResultState.APPROACHING_BREACH
        if consumed >= APPROACHING_BREACH_RATIO
        else ObjectiveResultState.PENDING
    )
    return _result(assignment, state, None, False, "pending", 0, ("timestamp_not_yet_observed",))


def _result(a, state, actual, breach, evidence, coverage, reasons):
    return IncidentObjectiveResult(
        incident_id=a.incident_id,
        definition_id=a.objective_definition_id,
        metric_type=a.metric_type,
        state=state,
        target_duration_seconds=a.target_duration_seconds,
        actual_duration_seconds=actual,
        historical_breach=breach,
        evidence_status=evidence,
        coverage=coverage,
        reason_codes=reasons,
    )


def evaluate_objective(
    definition: IncidentResponseObjectiveDefinition,
    results: Iterable[IncidentObjectiveResult],
    *,
    window_start: datetime,
    window_end: datetime,
    evaluated_at: datetime,
    short_window_counts: tuple[int, int] | None = None,
    long_window_counts: tuple[int, int] | None = None,
) -> IncidentResponseObjectiveEvaluation:
    items = tuple(results)
    met_states = {ObjectiveResultState.MET, ObjectiveResultState.WITHIN_TARGET}
    met = sum(x.state in met_states for x in items)
    breached = sum(
        x.historical_breach or x.state in {ObjectiveResultState.BREACHED, ObjectiveResultState.MET_AFTER_BREACH}
        for x in items
    )
    unknown = sum(x.state == ObjectiveResultState.UNAVAILABLE for x in items)
    excluded = sum(x.state in {ObjectiveResultState.EXCLUDED, ObjectiveResultState.NOT_APPLICABLE} for x in items)
    eligible = len(items) - excluded
    known = met + breached
    budget = calculate_error_budget(objective=definition.objective, eligible=eligible, bad=breached)
    sw = short_window_counts or (eligible, breached)
    lw = long_window_counts or (eligible, breached)
    short_burn, short_reason = calculate_burn_rate(objective=definition.objective, eligible=sw[0], bad=sw[1])
    long_burn, long_reason = calculate_burn_rate(objective=definition.objective, eligible=lw[0], bad=lw[1])
    classification, reasons = classify_multi_window_burn(short_burn, long_burn)
    reasons.extend(x for x in (short_reason, long_reason) if x)
    burn = BurnSignal(
        short_window_burn=short_burn, long_window_burn=long_burn, classification=classification, reason_codes=reasons
    )
    return IncidentResponseObjectiveEvaluation(
        definition_id=definition.id,
        definition_revision=definition.definition_revision,
        tenant_id=definition.tenant_id,
        environment=definition.environment,
        window_start=window_start,
        window_end=window_end,
        eligible_count=eligible,
        met_count=met,
        breached_count=breached,
        unknown_count=unknown,
        excluded_count=excluded,
        coverage_ratio=known / eligible if eligible else 0,
        actual_compliance=met / known if known else None,
        objective=definition.objective,
        error_budget=budget,
        burn=burn,
        state="unknown" if not known else ("healthy" if met / known >= definition.objective else "at_risk"),
        evaluated_at=evaluated_at,
    )
