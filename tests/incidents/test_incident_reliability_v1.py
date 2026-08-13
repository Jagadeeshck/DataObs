from datetime import datetime, timedelta, timezone

from services.incident_manager.reliability.evaluation import evaluate_incident, evaluate_objective
from services.incident_manager.reliability.models import (
    IncidentResponseObjectiveAssignment,
    IncidentResponseObjectiveDefinition,
    ObjectiveResultState,
    ResponseMetricType,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def definition(**changes):
    values = dict(
        id="ack-p1",
        tenant_id="t",
        environment="prod",
        name="P1 acknowledgement",
        metric_type=ResponseMetricType.TIME_TO_ACKNOWLEDGE,
        target_duration_seconds=300,
        objective=0.95,
        evaluation_window="30d",
        state="active",
        created_by="ops",
        created_at=NOW,
        updated_at=NOW,
    )
    values.update(changes)
    return IncidentResponseObjectiveDefinition(**values)


def assignment(**changes):
    value = IncidentResponseObjectiveAssignment.snapshot(
        definition(), incident_id="i", effective_at=NOW, source_incident_revision="2:1"
    )
    return value.model_copy(update=changes)


def test_acknowledgement_target_met():
    assert (
        evaluate_incident(assignment(), now=NOW + timedelta(minutes=3), observed_at=NOW + timedelta(minutes=3)).state
        == ObjectiveResultState.MET
    )


def test_acknowledgement_target_breached_and_late_remains_historical_breach():
    result = evaluate_incident(assignment(), now=NOW + timedelta(minutes=9), observed_at=NOW + timedelta(minutes=9))
    assert result.state == ObjectiveResultState.MET_AFTER_BREACH and result.historical_breach


def test_missing_timestamp_not_zero_and_approaching_breach():
    result = evaluate_incident(assignment(), now=NOW + timedelta(minutes=4), observed_at=None)
    assert result.actual_duration_seconds is None and result.state == ObjectiveResultState.APPROACHING_BREACH


def test_incident_slo_exposes_denominators_and_canonical_zero_budget():
    d = definition(objective=1)
    a = IncidentResponseObjectiveAssignment.snapshot(d, incident_id="i", effective_at=NOW, source_incident_revision="1")
    result = evaluate_incident(a, now=NOW + timedelta(minutes=6), observed_at=None)
    evaluation = evaluate_objective(
        d, [result], window_start=NOW, window_end=NOW + timedelta(days=1), evaluated_at=NOW + timedelta(days=1)
    )
    assert (evaluation.eligible_count, evaluation.breached_count) == (1, 1)
    assert evaluation.error_budget.status == "zero_error_budget"
