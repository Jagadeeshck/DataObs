"""Explainable dbt test history and coverage calculations."""

from __future__ import annotations

from typing import Any


def evaluate_test_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    bounded = history[-100:]
    statuses = [str(item.get("status", "unknown")) for item in bounded]
    counts = {status: statuses.count(status) for status in ("pass", "warn", "fail", "error", "skipped", "unknown")}
    executions = len(statuses)
    failures = counts["fail"] + counts["error"]
    transitions = sum(a != b for a, b in zip(statuses, statuses[1:]))
    if not executions: state = "never_observed"
    elif failures == executions: state = "consistently_failing"
    elif executions >= 5 and failures and counts["pass"] >= 2 and transitions >= 2: state = "flaky_candidate"
    elif statuses[-1] in {"fail", "error"}: state = "failing"
    elif statuses[-1] == "warn": state = "warning"
    elif statuses[-1] == "pass": state = "healthy"
    else: state = "unknown"
    return {"execution_count": executions, **{f"{key}_count": value for key, value in counts.items()}, "failure_rate": failures / executions if executions else None, "warning_rate": counts["warn"] / executions if executions else None, "state_transition_count": transitions, "flakiness_score": (transitions / max(executions - 1, 1)) * (counts["pass"] / executions) if executions else 0.0, "confidence": min(1.0, executions / 10), "health_state": state}


def calculate_coverage(resources: list[dict[str, Any]]) -> dict[str, Any]:
    models = [item for item in resources if item["resource_type"] == "model"]
    tests = [item for item in resources if item["resource_type"] == "test"]
    tested = {dependency for test in tests for dependency in test.get("dependencies", [])}
    columns = [(model["unique_id"], column["name"]) for model in models for column in model.get("columns", [])]
    targets = {(dependency, column) for test in tests for dependency in test.get("dependencies", []) for column in test.get("target_columns", [])}
    return {"total_models": len(models), "models_with_tests": sum(model["unique_id"] in tested for model in models), "total_documented_columns": len(columns), "columns_with_any_test": sum(item in targets for item in columns), "signal": "coverage_gap" if len(tested) < len(models) else "covered"}
