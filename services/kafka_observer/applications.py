from __future__ import annotations

from typing import Any

VALID_CONFIDENCE = {"observed", "strongly_correlated", "weakly_correlated", "declared", "unknown"}


def resolve_application(evidence: dict[str, Any]) -> dict[str, Any]:
    service = evidence.get("service.name")
    durable = evidence.get("durable_job_id")
    if service:
        confidence, evidence_type, app_id = "observed", "otel_messaging_span", service
    elif durable:
        confidence, evidence_type, app_id = "strongly_correlated", "durable_job", durable
    else:
        confidence, evidence_type, app_id = "unknown", "none", None
    return {"application_id": app_id, "evidence_type": evidence_type, "confidence": confidence}
