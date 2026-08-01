"""Bounded Spark application/stage/streaming evidence normalisation."""

from typing import Any

from services.spark_observer.aggregation import summarize


def normalize_spark_event(value: dict[str, Any]) -> dict[str, Any]:
    application_id = str(value.get("application_id") or value.get("app_id") or "")[:512]
    if not application_id:
        raise ValueError("Spark application_id is required")
    tasks = value.get("tasks") or []
    if not isinstance(tasks, list) or len(tasks) > 10000:
        raise ValueError("Spark task evidence exceeds its bound")
    return {
        "platform": "spark",
        "application_id": application_id,
        "job_id": value.get("job_id"),
        "stage_id": value.get("stage_id"),
        "attempt": max(0, int(value.get("attempt", 0))),
        "executor_summary": value.get("executor_summary") or {},
        "task_summary": summarize(tasks),
        "streaming_query_id": value.get("streaming_query_id"),
    }
