from datetime import datetime, timedelta, timezone

from services.monitoring.staleness import monitor_staleness


def test_staleness_respects_schedule_and_bounded_grace():
    now = datetime.now(timezone.utc)
    result = monitor_staleness(
        state="enabled", interval="5m", last_observation_at=now - timedelta(minutes=11), now=now, runtime_available=True
    )
    assert result.stale is True
    assert "schedule_grace_exceeded" in result.reason_codes


def test_missing_observation_is_unknown_and_missing_runtime_lowers_confidence():
    result = monitor_staleness(state="enabled", interval="5m", last_observation_at=None)
    assert result.stale is None
    assert result.confidence < 1


def test_inactive_monitor_staleness_is_not_applicable():
    result = monitor_staleness(state="archived", interval="5m", last_observation_at=None)
    assert result.stale is None
    assert result.reason_codes == ("staleness_not_applicable",)
