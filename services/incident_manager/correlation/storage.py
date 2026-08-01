from __future__ import annotations

from datetime import datetime
from typing import Any

from .contracts import CorrelationDecision, CorrelationGroup, EvidenceState, FeatureResult

GROUP_FIELDS = frozenset(
    {
        "id",
        "tenant_id",
        "environment",
        "correlation_id",
        "correlation_key",
        "correlation_version",
        "incident_id",
        "resource_ids",
        "affected_assets",
        "data_product_ids",
        "business_services",
        "severity",
        "confidence",
        "occurrence_count",
        "first_observed_at",
        "last_observed_at",
        "created_at",
        "updated_at",
        "status",
        "correlation_explanation",
        "metadata",
    }
)
EVENT_FIELDS = frozenset(
    {
        "@timestamp",
        "tenant_id",
        "environment",
        "correlation_id",
        "correlation_key",
        "correlation_version",
        "incident_id",
        "policy_id",
        "status",
        "confidence",
        "reason_code",
        "correlation_explanation",
        "metadata",
    }
)


def group_to_document(group: CorrelationGroup) -> dict[str, Any]:
    sample = sorted(set(group.member_incident_ids))[:100]
    metadata = dict(group.metadata)
    metadata.update(
        {
            "policy_version": group.policy_version,
            "representative_incident_id": group.representative_incident_id,
            "member_count": group.total_member_count,
            "members_truncated": group.members_truncated,
            "reason_codes": group.reason_codes[:50],
            "evidence_coverage": group.evidence_coverage,
            "flood_state": group.flood_state,
            "notification_decision": group.notification_decision,
        }
    )
    return {
        "id": group.id,
        "tenant_id": group.tenant_id,
        "environment": group.environment,
        "correlation_id": group.id,
        "correlation_key": group.id,
        "correlation_version": group.policy_version,
        "incident_id": group.representative_incident_id,
        "resource_ids": sample,
        "affected_assets": sorted(set(metadata.get("affected_assets", [])))[:100],
        "data_product_ids": sorted(set(metadata.get("data_product_ids", [])))[:100],
        "business_services": sorted(set(metadata.get("business_services", [])))[:100],
        "severity": group.highest_severity,
        "confidence": group.confidence,
        "occurrence_count": group.total_occurrence_count,
        "first_observed_at": group.first_observed_at.isoformat(),
        "last_observed_at": group.last_observed_at.isoformat(),
        "created_at": (group.created_at or group.first_observed_at).isoformat(),
        "updated_at": (group.updated_at or group.last_observed_at).isoformat(),
        "status": "active",
        "correlation_explanation": {"wording": "Evidence indicates association, not causation."},
        "metadata": metadata,
    }


def document_to_group(source: dict[str, Any]) -> CorrelationGroup:
    m = source.get("metadata", {})
    return CorrelationGroup(
        id=source["correlation_id"],
        tenant_id=source["tenant_id"],
        environment=source["environment"],
        policy_version=source["correlation_version"],
        representative_incident_id=source["incident_id"],
        member_incident_ids=list(source.get("resource_ids", [])),
        total_member_count=int(m.get("member_count", 0)),
        total_occurrence_count=int(source.get("occurrence_count", 0)),
        first_observed_at=datetime.fromisoformat(source["first_observed_at"]),
        last_observed_at=datetime.fromisoformat(source["last_observed_at"]),
        highest_severity=source["severity"],
        confidence=float(source.get("confidence", 0)),
        reason_codes=list(m.get("reason_codes", [])),
        evidence_coverage=float(m.get("evidence_coverage", 0)),
        members_truncated=bool(m.get("members_truncated", False)),
        flood_state=str(m.get("flood_state", "normal")),
        notification_decision=str(m.get("notification_decision", "notify")),
        created_at=datetime.fromisoformat(source["created_at"]),
        updated_at=datetime.fromisoformat(source["updated_at"]),
        metadata=dict(m),
    )


def decision_to_document(tenant_id: str, environment: str, decision: CorrelationDecision) -> dict[str, Any]:
    return {
        "@timestamp": decision.evaluated_at.isoformat(),
        "tenant_id": tenant_id,
        "environment": environment,
        "correlation_id": decision.decision_id,
        "correlation_key": decision.group_id or "none",
        "correlation_version": decision.policy_version,
        "incident_id": decision.incident_id,
        "policy_id": decision.policy_name,
        "status": decision.action,
        "confidence": decision.confidence,
        "reason_code": decision.reason_codes[0],
        "correlation_explanation": {"wording": decision.wording, "score": decision.score},
        "metadata": {
            "policy_hash": decision.policy_hash,
            "reason_codes": decision.reason_codes[:50],
            "missing_inputs": decision.missing_inputs[:50],
            "features": [f"{f.name}:{f.state}" for f in decision.features[:50]],
        },
    }


def document_to_decision(source: dict[str, Any]) -> CorrelationDecision:
    metadata = source.get("metadata", {})
    features = tuple(FeatureResult(*value.split(":", 1)) for value in metadata.get("features", []))
    features = tuple(FeatureResult(f.name, EvidenceState(f.state)) for f in features)
    return CorrelationDecision(
        source["correlation_id"],
        source["status"],
        source["incident_id"],
        None if source["correlation_key"] == "none" else source["correlation_key"],
        source["policy_id"],
        source["correlation_version"],
        metadata.get("policy_hash", ""),
        datetime.fromisoformat(source["@timestamp"]),
        float(source.get("correlation_explanation", {}).get("score", 0)),
        float(source.get("confidence", 0)),
        features,
        tuple(metadata.get("reason_codes", [])),
        tuple(metadata.get("missing_inputs", [])),
    )


def decision_to_api(decision: CorrelationDecision) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "action": decision.action,
        "incident_id": decision.incident_id,
        "group_id": decision.group_id,
        "policy_name": decision.policy_name,
        "policy_version": decision.policy_version,
        "policy_hash": decision.policy_hash,
        "evaluated_at": decision.evaluated_at.isoformat(),
        "score": decision.score,
        "confidence": decision.confidence,
        "reason_codes": list(decision.reason_codes),
        "missing_inputs": list(decision.missing_inputs),
        "wording": decision.wording,
    }
