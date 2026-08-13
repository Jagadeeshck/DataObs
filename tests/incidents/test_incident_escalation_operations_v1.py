from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from services.incident_manager.reliability.operations import (
    EscalationLevel,
    EscalationTrigger,
    IncidentEscalationPolicy,
    IncidentEscalationStore,
    IncidentStalenessPolicy,
    StalenessState,
    TimelineEvent,
    evaluate_operational_state,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
POLICY = IncidentStalenessPolicy(aging_after_seconds=60, stale_after_seconds=120, critically_stale_after_seconds=240)


def state(minutes=3, event_type=None, incident_state="open", terminal_at=None):
    opened = NOW - timedelta(minutes=minutes)
    events = []
    if event_type:
        events = [TimelineEvent(event_id="e", event_type=event_type, occurred_at=NOW - timedelta(seconds=30))]
    return evaluate_operational_state(
        opened_at=opened,
        incident_state=incident_state,
        timeline=events,
        now=NOW,
        policy=POLICY,
        terminal_at=terminal_at,
    )


def test_meaningful_progress_updates_staleness_clock():
    assert state(event_type="operator_progress_recorded").staleness_state == StalenessState.FRESH


def test_metadata_write_does_not_reset_staleness():
    assert state(event_type="tag_changed").staleness_state == StalenessState.STALE


def test_new_incident_uses_opened_at_as_initial_progress():
    assert state(minutes=0).last_meaningful_progress_at == NOW


def test_stale_incident():
    assert state().staleness_state == StalenessState.STALE


def test_critically_stale_incident():
    assert state(5).staleness_state == StalenessState.CRITICALLY_STALE


def test_resolved_incident_not_stale():
    assert (
        state(5, incident_state="resolved", terminal_at=NOW - timedelta(minutes=1)).staleness_state
        == StalenessState.FRESH
    )


def test_closed_incident_not_stale():
    assert state(5, incident_state="closed").staleness_duration_ms is None


def evaluate(
    store, at=NOW, triggers=(EscalationTrigger.ACKNOWLEDGEMENT_TARGET_BREACHED,), tenant="t", environment="prod"
):
    return store.evaluate(
        tenant_id=tenant,
        environment=environment,
        incident_id="i",
        triggers=triggers,
        now=at,
        policy=IncidentEscalationPolicy(level_2_after_seconds=60, level_3_after_seconds=120, cooldown_seconds=0),
        source_incident_revision="1",
        source_reliability_revision="r1",
    )


def test_objective_breach_creates_escalation():
    assert evaluate(IncidentEscalationStore())[0].current_level == EscalationLevel.LEVEL_1


def test_escalation_is_idempotent():
    store = IncidentEscalationStore()
    evaluate(store)
    assert evaluate(store) == () and len(store.events("t", "prod", "i")) == 1


def test_same_worker_cycle_does_not_duplicate_event():
    test_escalation_is_idempotent()


def test_escalation_advances_after_policy_delay():
    store = IncidentEscalationStore()
    evaluate(store)
    assert evaluate(store, NOW + timedelta(seconds=61))[0].current_level == EscalationLevel.LEVEL_2


def test_escalation_does_not_repeat_same_level():
    store = IncidentEscalationStore()
    evaluate(store)
    evaluate(store, NOW + timedelta(seconds=61))
    assert evaluate(store, NOW + timedelta(seconds=62)) == ()


def test_clear_condition_clears_escalation():
    store = IncidentEscalationStore()
    evaluate(store)
    assert evaluate(store, triggers=())[0].active is False


def test_escalation_does_not_change_severity():
    store = IncidentEscalationStore()
    assert "severity" not in type(evaluate(store)[0]).model_fields


def test_two_workers_create_one_logical_escalation():
    store = IncidentEscalationStore()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: evaluate(store), range(2)))
    assert len(store.list("t", "prod")) == len(store.events("t", "prod", "i")) == 1


def test_incident_ack_and_escalation_ack_are_distinct():
    store = IncidentEscalationStore()
    escalation = evaluate(store)[0]
    acknowledged = store.acknowledge("t", "prod", "i", escalation.id, at=NOW)
    assert acknowledged.acknowledged_at == NOW and acknowledged.active


def test_cross_tenant_escalation_impossible():
    store = IncidentEscalationStore()
    evaluate(store)
    assert store.list("other", "prod") == ()


def test_cross_environment_escalation_impossible():
    store = IncidentEscalationStore()
    evaluate(store)
    assert store.list("t", "dev") == ()
