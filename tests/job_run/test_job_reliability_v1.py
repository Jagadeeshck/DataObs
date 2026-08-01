from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.job_run import JobSchedule, ReliabilityPolicy, ScheduleSource
from services.job_reliability.cursor import CursorCodec, InvalidCursor
from services.job_reliability.evaluator import calculate_reliability
from services.job_reliability.schedule import generate_expected_runs

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def policy(**updates):
    values = dict(
        tenant_id="t1",
        environment="prod",
        job_id="j1",
        schedule_source=ScheduleSource.CONFIGURED,
        expected_schedule=JobSchedule(kind="interval", expression="3600", confidence=1),
        etag="e1",
        created_at=NOW,
        updated_at=NOW,
    )
    values.update(updates)
    return ReliabilityPolicy(**values)


def test_interval_and_non_periodic_semantics():
    assert len(generate_expected_runs(policy(), NOW, NOW + timedelta(hours=3))) == 3
    assert (
        generate_expected_runs(policy(expected_schedule=JobSchedule(kind="event_driven")), NOW, NOW + timedelta(days=1))
        == []
    )
    assert (
        generate_expected_runs(policy(expected_schedule=JobSchedule(kind="ad_hoc")), NOW, NOW + timedelta(days=1)) == []
    )


def test_inferred_schedule_requires_confidence():
    p = policy(
        schedule_source=ScheduleSource.INFERRED,
        expected_schedule=JobSchedule(kind="interval", expression="60", confidence=0.5),
    )
    assert generate_expected_runs(p, NOW, NOW + timedelta(minutes=2)) == []


def test_missing_is_not_zero_and_weights_normalize():
    result = calculate_reliability(
        policy(component_weights={"success": 3, "retry": 1}),
        {"success": 0.0, "retry": None},
        {"success": 3},
        NOW,
        NOW + timedelta(hours=1),
    )
    assert result.score == 0.0
    assert result.normalized_weights == {"success": 1.0}
    assert result.missing_components == ["retry"]


def test_cursor_is_scope_filter_and_expiry_bound():
    codec = CursorCodec(b"x" * 32, ttl_seconds=10)
    token = codec.encode(
        resource="jobs",
        tenant_id="t1",
        environment="prod",
        filters={"state": "failed"},
        sort=["id"],
        values=["j1"],
        now=100,
    )
    assert codec.decode(
        token, resource="jobs", tenant_id="t1", environment="prod", filters={"state": "failed"}, sort=["id"], now=105
    )["values"] == ["j1"]
    with pytest.raises(InvalidCursor):
        codec.decode(
            token,
            resource="runs",
            tenant_id="t1",
            environment="prod",
            filters={"state": "failed"},
            sort=["id"],
            now=105,
        )
    with pytest.raises(InvalidCursor):
        codec.decode(
            token,
            resource="jobs",
            tenant_id="t1",
            environment="prod",
            filters={"state": "failed"},
            sort=["id"],
            now=111,
        )
    with pytest.raises(InvalidCursor):
        codec.decode(
            token[:-1] + ("A" if token[-1] != "A" else "B"),
            resource="jobs",
            tenant_id="t1",
            environment="prod",
            filters={"state": "failed"},
            sort=["id"],
            now=105,
        )
