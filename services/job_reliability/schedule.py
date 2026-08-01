"""Bounded, timezone-aware expected-run generation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from packages.domain_model.job_run import ExpectedRun, ExpectedRunState, ReliabilityPolicy, ScheduleSource

MAX_EXPECTED_RUNS = 10_000


def _identifier(policy: ReliabilityPolicy, scheduled: datetime) -> str:
    value = f"{policy.tenant_id}\0{policy.environment}\0{policy.job_id}\0{scheduled.isoformat()}\0{policy.revision}"
    return hashlib.sha256(value.encode()).hexdigest()


def _cron_matches(value: datetime, expression: str) -> bool:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("cron schedule must contain five fields")
    actual = [value.minute, value.hour, value.day, value.month, value.weekday()]
    for token, number in zip(fields, actual):
        if token == "*":
            continue
        if token.startswith("*/") and number % int(token[2:]) == 0:
            continue
        if token.isdigit() and int(token) == number:
            continue
        return False
    return True


def generate_expected_runs(policy: ReliabilityPolicy, start: datetime, end: datetime) -> list[ExpectedRun]:
    """Generate only actionable interval/cron expectations within a finite UTC range."""
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("evaluation bounds must be timezone-aware")
    if end <= start or not policy.enabled or not policy.expected_schedule:
        return []
    schedule = policy.expected_schedule
    if schedule.kind not in {"interval", "cron"}:
        return []
    if policy.schedule_source == ScheduleSource.UNKNOWN:
        return []
    if policy.schedule_source == ScheduleSource.INFERRED and schedule.confidence < 0.8:
        return []
    zone = ZoneInfo(policy.timezone)
    cursor = start.astimezone(zone).replace(second=0, microsecond=0)
    candidates: list[datetime] = []
    if schedule.kind == "interval":
        try:
            seconds = int(schedule.expression or "0")
        except ValueError as exc:
            raise ValueError("interval expression must be seconds") from exc
        if seconds <= 0:
            raise ValueError("interval must be positive")
        cursor = start.astimezone(zone)
        while cursor < end.astimezone(zone):
            candidates.append(cursor)
            cursor += timedelta(seconds=seconds)
            if len(candidates) > MAX_EXPECTED_RUNS:
                raise ValueError("expected-run range exceeds bound")
    else:
        while cursor < end.astimezone(zone):
            if cursor >= start.astimezone(zone) and _cron_matches(cursor, schedule.expression or ""):
                candidates.append(cursor)
            cursor += timedelta(minutes=1)
            if (cursor - start.astimezone(zone)).total_seconds() / 60 > 525_600:
                raise ValueError("cron evaluation range exceeds one year")
    result = []
    for scheduled in candidates:
        excluded = next(
            (w.reason or "maintenance" for w in policy.maintenance_windows if w.starts_at <= scheduled <= w.ends_at),
            None,
        )
        status = ExpectedRunState.EXCLUDED_BY_MAINTENANCE if excluded else ExpectedRunState.EXPECTED
        result.append(
            ExpectedRun(
                tenant_id=policy.tenant_id,
                environment=policy.environment,
                expected_run_id=_identifier(policy, scheduled),
                job_id=policy.job_id,
                scheduled_at=scheduled,
                permitted_start_at=scheduled,
                permitted_start_until=scheduled + timedelta(seconds=policy.allowed_start_delay_seconds),
                deadline_at=(
                    scheduled + timedelta(seconds=policy.completion_deadline_seconds)
                    if policy.completion_deadline_seconds
                    else None
                ),
                schedule_source=policy.schedule_source,
                schedule_confidence=schedule.confidence,
                status=status,
                maintenance_exclusion=excluded,
                evaluated_at=end,
            )
        )
    return result
