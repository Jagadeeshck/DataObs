import hashlib
import json

from .redaction import redact_connector_config


def normalize_connector(name: str, config: dict, status: dict) -> dict:
    safe = redact_connector_config(config)
    tasks = status.get("tasks", [])[:1000]
    task_states = [{"id": task.get("id"), "state": task.get("state")} for task in tasks]
    return {
        "connector_id": name,
        "name": name,
        "connector_type": "source" if "source" in str(config.get("connector.class", "")).lower() else "sink",
        "state": status.get("connector", {}).get("state", "UNKNOWN"),
        "task_count": len(tasks),
        "failed_task_count": sum(task.get("state") == "FAILED" for task in tasks),
        "task_states": task_states,
        "worker_ids": sorted({task.get("worker_id") for task in tasks if task.get("worker_id")})[:100],
        "config": safe,
        "class_fingerprint": hashlib.sha256(str(config.get("connector.class", "")).encode()).hexdigest(),
        "config_fingerprint": hashlib.sha256(json.dumps(safe, sort_keys=True).encode()).hexdigest(),
    }
