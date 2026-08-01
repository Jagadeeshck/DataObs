from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.job_run import ExpectedRunState, JobSchedule, ReliabilityPolicy, ScheduleSource
from services.job_reliability.association import associate_actual_run
from services.job_reliability.repository import ConflictError, MemoryReliabilityRepository
from services.job_reliability.run_evaluator import evaluate_run
from services.job_reliability.schedule import generate_expected_runs
from services.job_reliability.service import ReliabilityService

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def policy(**values):
    defaults = dict(
        tenant_id="t1",
        environment="prod",
        job_id="j1",
        schedule_source=ScheduleSource.CONFIGURED,
        expected_schedule=JobSchedule(kind="interval", expression="3600", confidence=1),
        allowed_start_delay_seconds=600,
        etag="one",
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(values)
    return ReliabilityPolicy(**defaults)


def test_expected_runs_are_idempotent_and_business_exclusions_are_evidence():
    repo = MemoryReliabilityRepository()
    values = generate_expected_runs(policy(business_calendar_exclusions=["2026-01-01"]), NOW, NOW + timedelta(hours=2))
    assert values[0].status == ExpectedRunState.EXCLUDED_BY_MAINTENANCE
    assert values[0].reason_codes == ["business_calendar_exclusion"]
    assert repo.create_expected_run(values[0]) is True
    assert repo.create_expected_run(values[0]) is False


def test_association_is_tenant_job_bound_and_prefers_exact_schedule():
    expected = generate_expected_runs(policy(), NOW, NOW + timedelta(hours=2))
    exact = associate_actual_run(
        tenant_id="t1",
        environment="prod",
        job_id="j1",
        run_id="r1",
        started_at=NOW + timedelta(minutes=4),
        scheduled_at=NOW,
        expected_runs=expected,
    )
    assert exact.expected_run_id == expected[0].expected_run_id
    assert exact.reason_codes == ("exact_scheduled_time",)
    denied = associate_actual_run(
        tenant_id="other", environment="prod", job_id="j1", run_id="r1", started_at=NOW, expected_runs=expected
    )
    assert denied.expected_run_id is None


def test_unknown_duration_and_retry_evidence_never_pass():
    result = evaluate_run(
        {"run_id": "r1", "state": "success", "started_at": NOW},
        policy(maximum_duration_ms=1000),
        expected=None,
        evaluated_at=NOW,
    )
    assert result.duration_result is None
    assert result.retry_result is None
    assert {"duration", "retry_evidence"} <= set(result.missing_inputs)


def test_policy_history_occ_and_fenced_checkpoint():
    repo = MemoryReliabilityRepository()
    first = policy()
    repo.put_policy(first, None)
    second = policy(revision=2, etag="two")
    with pytest.raises(ConflictError):
        repo.put_policy(second, "bad")
    repo.put_policy(second, "one")
    assert [x.revision for x in repo.list_policy_history("t1", "prod", "j1")] == [1, 2]
    token = repo.claim_lease("t1:prod", "worker-a", NOW, 10)
    with pytest.raises(ConflictError):
        repo.update_checkpoint("t1:prod", "worker-b", token, NOW)


def test_runtime_advances_only_after_durable_writes():
    repo = MemoryReliabilityRepository()
    repo.put_policy(policy(), None)
    service = ReliabilityService(repo, owner="worker", clock=lambda: NOW + timedelta(hours=2))
    result = service.once("t1", "prod", ["j1"])
    assert result.checkpoint_advanced is True
    assert result.expected_runs_generated > 0
