from datetime import datetime
from typing import Any, Dict

from .deduplication import deterministic_event_id
from .facets import preserve_facets
from .validation import event_type


def normalize(payload: Dict[str, Any], binding) -> Dict[str, Any]:
    kind = event_type(payload)
    eid = deterministic_event_id(payload, binding.source_id)
    run = payload.get("run", {})
    job = payload.get("job", {})
    return {
        "event_id": eid,
        "event_type": kind,
        "tenant_id": binding.tenant_id,
        "environment": binding.environment,
        "source_id": binding.source_id,
        "event_time": datetime.fromisoformat(payload["eventTime"].replace("Z", "+00:00")),
        "source_state": payload.get("eventType") if kind == "RunEvent" else None,
        "source_run_id": run.get("runId"),
        "namespace": job.get("namespace"),
        "job_name": job.get("name"),
        "openlineage_facets": preserve_facets(payload),
    }
