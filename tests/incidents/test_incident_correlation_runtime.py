from copy import deepcopy
from datetime import datetime, timedelta, timezone

from packages.domain_model.incident import Incident
from services.incident_manager.correlation.coordinator import IncidentCorrelationCoordinator
from services.incident_manager.correlation.repository import InMemoryCorrelationRepository
from services.incident_manager.correlation.storage import (
    EVENT_FIELDS,
    GROUP_FIELDS,
    decision_to_document,
    group_to_document,
)
from services.incident_manager.flood_control.contracts import FloodEvent, FloodState, FloodWindow
from services.incident_manager.flood_control.evaluator import evaluate_flood
from services.incident_manager.flood_control.policy import FloodPolicy
from services.incident_manager.flood_control.repository import InMemoryFloodRepository
from services.incident_manager.repository import InMemoryIncidentRepository
from services.incident_manager.service import IncidentManagerService

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def make_incident(identifier: str, asset: str = "asset-1") -> Incident:
    return Incident(
        id=identifier,
        tenant_id="tenant-a",
        environment="prod",
        deduplication_key=identifier,
        affected_assets=[asset],
        first_observed_at=NOW,
        last_observed_at=NOW,
        opened_at=NOW,
    )


def runtime():
    incidents = InMemoryIncidentRepository()
    correlations = InMemoryCorrelationRepository()
    floods = InMemoryFloodRepository()
    return incidents, correlations, floods, IncidentCorrelationCoordinator(incidents, correlations, floods)


def test_three_members_reuse_stable_group_and_replay_is_exact():
    incidents, correlations, floods, coordinator = runtime()
    ids = []
    for name in ("one", "two", "three"):
        item = incidents.create_incident(make_incident(name))
        result = coordinator.process(item)
        ids.append(result["correlation"]["group_id"])
    assert len(set(ids)) == 1
    group = correlations.get_group("tenant-a", "prod", ids[0])
    assert group and group.group.total_member_count == 3
    before = (group.group.total_occurrence_count, len(correlations.decisions), len(floods.transitions))
    replay = coordinator.process(incidents.get_incident("tenant-a", "three", "prod"))
    after_group = correlations.get_group("tenant-a", "prod", ids[0])
    assert replay["correlation"]["status"] == "replayed"
    assert (
        after_group
        and (after_group.group.total_occurrence_count, len(correlations.decisions), len(floods.transitions)) == before
    )


def test_scope_isolation_and_strict_adapters():
    incidents, correlations, _, coordinator = runtime()
    item = incidents.create_incident(make_incident("one"))
    result = coordinator.process(item)
    stored = correlations.get_group("tenant-a", "prod", result["correlation"]["group_id"])
    assert stored
    assert set(group_to_document(stored.group)) <= GROUP_FIELDS
    decision = next(iter(correlations.decisions.values()))[2]
    assert set(decision_to_document("tenant-a", "prod", decision)) <= EVENT_FIELDS
    assert correlations.get_group("tenant-b", "prod", stored.group.id) is None
    assert correlations.get_group("tenant-a", "dev", stored.group.id) is None


def test_immutable_flood_quiet_close_and_bypass_replay_safety():
    policy = FloodPolicy(
        elevated_count=1,
        flooding_count=2,
        event_rate_per_minute=999,
        unique_asset_threshold=999,
        quiet_period_seconds=10,
        hysteresis_count=0,
        maximum_events=2,
    )
    original = FloodWindow("f", "t", "prod", "g")
    decision, first = evaluate_flood(original, FloodEvent("one", NOW, "i1"), policy)
    assert original.events == {} and decision.new_state == FloodState.ELEVATED
    flooding, second = evaluate_flood(first, FloodEvent("two", NOW + timedelta(seconds=1), "i2"), policy)
    assert flooding.new_state == FloodState.FLOODING and second.suppressed_notification_count == 1
    replay, replayed = evaluate_flood(second, FloodEvent("two", NOW + timedelta(seconds=1), "i2"), policy)
    assert replayed.suppressed_notification_count == 1 and replay.observed["count"] == 2
    bypass, bypassed = evaluate_flood(
        replayed, FloodEvent("critical", NOW + timedelta(seconds=2), "i3", severity="critical"), policy
    )
    assert bypass.notification_decision == "escalate" and bypassed.suppressed_notification_count == 1
    recovering = deepcopy(bypassed)
    recovering.state = FloodState.RECOVERING
    recovering.last_transition_at = NOW
    closed, _ = evaluate_flood(
        recovering,
        FloodEvent("late", NOW + timedelta(hours=1), "i4"),
        FloodPolicy(elevated_count=99, flooding_count=100, quiet_period_seconds=10),
        quiet_at=NOW + timedelta(hours=1),
    )
    assert closed.new_state == FloodState.CLOSED


def test_ingestion_partial_failure_keeps_incident_and_defers():
    class BrokenCoordinator:
        def __init__(self):
            self.deferred = []

        def process(self, incident):
            raise RuntimeError("provider secret must not escape")

        def defer(self, incident, phase):
            self.deferred.append((incident.id, phase))

    repo = InMemoryIncidentRepository()
    broken = BrokenCoordinator()
    service = IncidentManagerService(repo, broken)
    result = service.ingest(
        {
            "environment": "prod",
            "source_event_id": "e1",
            "finding_type": "unknown",
            "signal_type": "monitor_anomaly",
            "asset_id": "a",
            "title": "x",
            "summary": "x",
            "first_observed_at": NOW.isoformat(),
            "last_observed_at": NOW.isoformat(),
        },
        tenant_id="tenant-a",
    )
    assert repo.get_incident("tenant-a", result["incident"]["id"], "prod")
    assert result["processing"]["status"] == "incident_persisted_correlation_deferred"
    assert broken.deferred
