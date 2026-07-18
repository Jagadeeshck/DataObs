from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packages.domain_model.incident import Finding, FindingType, Severity, SignalType

_TYPE_MAP = {
    "schema_change": (FindingType.SCHEMA_CHANGE, SignalType.POSTGRES_SCHEMA_CHANGE),
    "freshness": (FindingType.FRESHNESS_BREACH, SignalType.FRESHNESS_MEASUREMENT),
    "quality_result": (FindingType.DATA_QUALITY_FAILURE, SignalType.QUALITY_RESULT),
    "scanner_error": (FindingType.SCANNER_FAILURE, SignalType.SCANNER_ERROR),
    "source_unavailable": (FindingType.SOURCE_UNAVAILABLE, SignalType.SOURCE_CONNECTION_FAILURE),
    "openlineage_run_failure": (FindingType.SCANNER_FAILURE, SignalType.OPENLINEAGE_RUN_FAILURE),
    "profile_anomaly": (FindingType.PROFILE_ANOMALY, SignalType.MONITOR_ANOMALY),
}


def normalize_event(event: dict[str, Any], *, tenant_id: str) -> Finding:
    if event.get("tenant_id", tenant_id) != tenant_id:
        raise ValueError("cross-tenant finding event rejected")
    kind = event.get("event_type") or event.get("type") or "quality_result"
    finding_type, signal_type = _TYPE_MAP.get(kind, (FindingType.DATA_QUALITY_FAILURE, SignalType.QUALITY_RESULT))
    observed = event.get("observed_value") or {k: event[k] for k in ("status", "score", "error") if k in event}
    now = event.get("@timestamp") or event.get("observed_at") or datetime.now(timezone.utc)
    return Finding(
        tenant_id=tenant_id,
        environment=event.get("environment", "default"),
        finding_type=finding_type,
        signal_type=signal_type,
        source_event_id=str(event.get("id") or event.get("event_id") or event.get("run_id")),
        source_event_version=str(event.get("schema_version", "v1")),
        asset_id=str(event.get("asset_id") or event.get("table") or event.get("dataset") or "unknown"),
        source_id=event.get("source_id"),
        scanner_id=event.get("scanner_id"),
        monitor_id=event.get("monitor_id"),
        policy_id=event.get("policy_id"),
        title=event.get("title") or f"{finding_type.value} on {event.get('asset_id', 'asset')}",
        summary=event.get("summary") or event.get("message") or "DataObs normalized finding",
        observed_value=observed,
        expected_value=event.get("expected_value") or {},
        severity=Severity(event.get("severity", "medium")),
        confidence=float(event.get("confidence", 1.0)),
        evidence=event.get("evidence", []),
        owner_team=event.get("owner_team"),
        business_service=event.get("business_service"),
        downstream_impact=event.get("downstream_impact", []),
        downstream_asset_count=int(event.get("downstream_asset_count", len(event.get("downstream_impact", [])))),
        trace_id=event.get("trace_id") or event.get("otel_trace_id"),
        correlation_id=event.get("correlation_id"),
        first_observed_at=now,
        last_observed_at=now,
        status="recovered" if event.get("recovery_signal") else "active",
        recovery_signal=bool(event.get("recovery_signal", False)),
    )
