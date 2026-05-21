from __future__ import annotations
from datetime import datetime, timezone

def metric_doc(run_id: str, stage_name: str, input_rows: int, output_rows: int, status: str = "success", error_count: int = 0, run_mode: str = "good"):
    return {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "run_mode": run_mode,
        "scenario": "road_safety",
        "stage_name": stage_name,
        "stage_duration_seconds": max(0.1, round(output_rows / 50000, 3)),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "records_processed": output_rows,
        "rejected_rows": max(0, input_rows - output_rows),
        "failed_checks": error_count,
        "shuffle_read_bytes": input_rows * 120,
        "shuffle_write_bytes": output_rows * 90,
        "local_executor_count": 1,
        "driver_memory_mb": 512,
        "cpu_time_seconds": round(output_rows / 200000, 3),
        "status": "fail" if status not in {"success", "pass"} else "pass",
        "severity": "critical" if error_count else "info",
        "error_count": error_count,
    }
