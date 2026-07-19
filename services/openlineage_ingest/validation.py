from typing import Any, Dict


class EventValidationError(ValueError):
    pass


SUPPORTED = {"RunEvent", "JobEvent", "DatasetEvent"}


def event_type(payload: Dict[str, Any]) -> str:
    declared = payload.get("event_type")
    kind = declared if declared in SUPPORTED else None
    if not kind:
        if "run" in payload and "job" in payload:
            kind = "RunEvent"
        elif "job" in payload:
            kind = "JobEvent"
        elif "dataset" in payload or "inputs" in payload or "outputs" in payload:
            kind = "DatasetEvent"
    if kind not in SUPPORTED:
        raise EventValidationError("unsupported or missing OpenLineage event type")
    if not payload.get("eventTime"):
        raise EventValidationError("eventTime is required")
    return kind
