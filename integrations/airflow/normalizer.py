"""Bounded Airflow DAG/task evidence normalisation."""

from typing import Any


def normalize_airflow_event(value: dict[str, Any]) -> dict[str, Any]:
    dag_id = str(value.get("dag_id") or value.get("dagId") or "")[:512]
    run_id = str(value.get("dag_run_id") or value.get("run_id") or "")[:512]
    if not dag_id or not run_id:
        raise ValueError("Airflow DAG and DAG run IDs are required")
    return {
        "platform": "airflow",
        "dag_id": dag_id,
        "dag_run_id": run_id,
        "task_id": str(value.get("task_id") or "")[:512] or None,
        "try_number": max(1, int(value.get("try_number", 1))),
        "map_index": value.get("map_index"),
        "schedule": str(value.get("schedule") or "")[:1024] or None,
        "logical_date": value.get("logical_date"),
    }
