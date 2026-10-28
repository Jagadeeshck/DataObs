from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.incident_manager.flood_control.contracts import FloodEvent, FloodState, FloodWindow
from services.incident_manager.flood_control.evaluator import evaluate_flood
from services.incident_manager.flood_control.policy import FloodPolicy

NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def test_flooding_one_group_does_not_suppress_unrelated_group() -> None:
    policy = FloodPolicy(
        elevated_count=2,
        flooding_count=3,
        event_rate_per_minute=999,
        unique_asset_threshold=999,
        unique_source_threshold=999,
        maximum_events=50,
    )
    noisy = FloodWindow("flood-noisy", "tenant-a", "production", "group-noisy")
    for number in range(3):
        decision, noisy = evaluate_flood(
            noisy,
            FloodEvent(
                f"noisy-{number}",
                NOW + timedelta(seconds=number),
                f"incident-noisy-{number}",
                asset_id="asset-noisy",
                source="monitor-noisy",
            ),
            policy,
        )

    assert noisy.state == FloodState.FLOODING
    assert decision.notification_decision == "coalesce"
    assert noisy.suppressed_notification_count == 1

    unrelated = FloodWindow("flood-unrelated", "tenant-a", "production", "group-unrelated")
    unrelated_decision, unrelated = evaluate_flood(
        unrelated,
        FloodEvent(
            "unrelated-1",
            NOW + timedelta(seconds=3),
            "incident-unrelated",
            asset_id="asset-unrelated",
            source="monitor-unrelated",
        ),
        policy,
    )

    assert unrelated.state == FloodState.NORMAL
    assert unrelated_decision.notification_decision == "notify"
    assert unrelated.suppressed_notification_count == 0


def test_high_volume_window_remains_bounded_and_replay_safe() -> None:
    policy = FloodPolicy(
        elevated_count=500,
        flooding_count=600,
        event_rate_per_minute=999,
        unique_asset_threshold=999,
        unique_source_threshold=999,
        maximum_events=50,
    )
    window = FloodWindow("flood-bounded", "tenant-a", "production", "group-bounded")

    for number in range(200):
        event = FloodEvent(
            f"event-{number}",
            NOW + timedelta(seconds=number),
            f"incident-{number}",
            asset_id="asset-1",
            source="monitor-1",
        )
        _, window = evaluate_flood(window, event, policy)

    assert len(window.events) == 50
    retained_before = tuple(sorted(window.events))
    replay_event = window.events[retained_before[-1]]

    replay, replayed = evaluate_flood(window, replay_event, policy)

    assert tuple(sorted(replayed.events)) == retained_before
    assert replayed.suppressed_notification_count == window.suppressed_notification_count
    assert replay.evidence_references.count(replay_event.event_id) == 1
