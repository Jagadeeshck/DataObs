"""Evidence-aware logical run evaluation."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from packages.domain_model.job_run import (
    ExpectedRun,
    FailureCategory,
    ReliabilityPolicy,
    RunReliabilityEvaluation,
    RunState,
)


def evaluate_run(
    run: dict[str, Any], policy: ReliabilityPolicy, *, expected: ExpectedRun | None, evaluated_at: datetime
) -> RunReliabilityEvaluation:
    started = run.get("started_at")
    ended = run.get("ended_at")
    if isinstance(started, str):
        started = datetime.fromisoformat(started.replace("Z", "+00:00"))
    if isinstance(ended, str):
        ended = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    missing: list[str] = []
    warnings: list[str] = []
    start_result = None
    deadline_result = None
    if expected and started:
        start_result = started <= expected.permitted_start_until
    elif expected:
        missing.append("actual_start")
    if expected and expected.deadline_at and ended:
        deadline_result = ended <= expected.deadline_at
    elif policy.completion_deadline_seconds:
        missing.append("completion_time")
    duration_result = None
    if policy.maximum_duration_ms is not None:
        if run.get("duration_ms") is None:
            missing.append("duration")
        else:
            duration_result = int(run["duration_ms"]) <= policy.maximum_duration_ms
    retry_result = None
    if "attempts" not in run and "retry_count" not in run:
        missing.append("retry_evidence")
    else:
        retry_result = int(run.get("retry_count", max(0, int(run.get("attempts", 1)) - 1))) == 0
    quality_result = None
    quality = run.get("quality_relationship")
    if quality and quality.get("classification") in {"direct", "correlated"}:
        quality_result = not bool(quality.get("failed"))
        if quality.get("classification") == "correlated":
            warnings.append("quality evidence is correlated, not root cause")
    else:
        missing.append("quality_evidence")
    dependency_result = None
    dependency = run.get("dependency_relationship")
    if dependency and dependency.get("classification") in {"direct", "correlated", "inferred"}:
        dependency_result = not bool(dependency.get("failed"))
    else:
        missing.append("dependency_evidence")
    failure = run.get("failure") or {}
    category = failure.get("category")
    try:
        failure_category = FailureCategory(category) if category else None
    except ValueError:
        failure_category = FailureCategory.UNKNOWN
    coverage = 1 - len(set(missing)) / 7
    identity = hashlib.sha256(
        f"{policy.tenant_id}\0{policy.environment}\0{run['run_id']}\0{policy.revision}\0{evaluated_at.isoformat()}".encode()
    ).hexdigest()
    return RunReliabilityEvaluation(
        tenant_id=policy.tenant_id,
        environment=policy.environment,
        evaluation_id=identity,
        job_id=policy.job_id,
        run_id=run["run_id"],
        expected_run_id=expected.expected_run_id if expected else None,
        run_state=RunState(run.get("state", "unknown")),
        start_delay_result=start_result,
        deadline_result=deadline_result,
        duration_result=duration_result,
        retry_result=retry_result,
        quality_result=quality_result,
        dependency_result=dependency_result,
        failure_category=failure_category,
        confidence=max(0.0, coverage),
        evidence_coverage=max(0.0, coverage),
        missing_inputs=sorted(set(missing)),
        warnings=warnings,
        evidence_references=list(run.get("evidence_references", []))[:100],
        evaluated_at=evaluated_at,
        policy_revision=policy.revision,
    )
