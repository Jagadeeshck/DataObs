from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

FEATURE_VERSION = "incident-features/1.0.0"
MAX_VALUES = 100


def _values(values: Iterable[Any] | None) -> tuple[str, ...]:
    """Canonicalize bounded categorical evidence; never accepts evidence blobs."""
    return tuple(
        sorted({str(value).strip().lower() for value in values or () if value is not None and str(value).strip()})
    )[:MAX_VALUES]


class FailureSignature(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    finding_types: tuple[str, ...] = ()
    resource_scope: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    error_categories: tuple[str, ...] = ()


class IncidentFeatures(BaseModel):
    """Safe structural evidence. Free text, timestamps and identities are deliberately absent."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tenant_id: str
    environment: str
    incident_id: str
    source_revision: str = "unknown"
    finding_types: tuple[str, ...] = ()
    signal_types: tuple[str, ...] = ()
    primary_asset: str | None = None
    affected_assets: tuple[str, ...] = ()
    resource_ids: tuple[str, ...] = ()
    scanner_ids: tuple[str, ...] = ()
    monitor_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    failure_categories: tuple[str, ...] = ()
    correlation_keys: tuple[str, ...] = ()
    correlation_feature_keys: tuple[str, ...] = ()
    data_product_ids: tuple[str, ...] = ()
    business_services: tuple[str, ...] = ()
    confirmed_root_cause_categories: tuple[str, ...] = ()
    contributing_factor_categories: tuple[str, ...] = ()
    resolution_reasons: tuple[str, ...] = ()
    remediation_action_types: tuple[str, ...] = ()
    workflow_types: tuple[str, ...] = ()
    recovery_characteristics: tuple[str, ...] = ()
    merged_from: tuple[str, ...] = ()
    split_from: str | None = None

    @property
    def failure_signature(self) -> FailureSignature:
        return FailureSignature(
            finding_types=self.finding_types,
            resource_scope=self.affected_assets,
            rule_ids=self.rule_ids,
            error_categories=self.failure_categories,
        )


def extract_features(
    incident: Any, findings: Iterable[Any] = (), confirmed_root_causes: Iterable[str] = ()
) -> IncidentFeatures:
    findings = tuple(findings)
    revision = f"{getattr(incident, 'seq_no', None)}:{getattr(incident, 'primary_term', None)}"
    primary = getattr(incident, "primary_resource", None)
    correlation = getattr(incident, "correlation_explanation", {}) or {}
    return IncidentFeatures(
        tenant_id=incident.tenant_id,
        environment=incident.environment,
        incident_id=incident.id,
        source_revision=revision,
        finding_types=_values(getattr(item, "finding_type", None) for item in findings),
        signal_types=_values(getattr(item, "signal_type", None) for item in findings),
        primary_asset=str(primary).strip().lower() if primary else None,
        affected_assets=_values(getattr(incident, "affected_assets", ())),
        resource_ids=_values(value for item in findings for value in getattr(item, "resource_ids", ())),
        scanner_ids=_values(getattr(item, "scanner_id", None) for item in findings),
        monitor_ids=_values(getattr(item, "monitor_id", None) for item in findings),
        rule_ids=_values((getattr(item, "rule_id", None) or getattr(item, "policy_id", None)) for item in findings),
        failure_categories=_values(
            getattr(item, "correlation_features", {}).get("failure_category") for item in findings
        ),
        correlation_keys=_values([getattr(incident, "correlation_key", None)]),
        correlation_feature_keys=_values(correlation.keys()),
        data_product_ids=_values(getattr(incident, "data_product_ids", ())),
        business_services=_values(getattr(incident, "business_services", ())),
        confirmed_root_cause_categories=_values(confirmed_root_causes),
        resolution_reasons=_values([getattr(incident, "resolution_reason", None)]),
        workflow_types=_values([getattr(incident, "workflow_ref", None)]),
        recovery_characteristics=_values([getattr(incident, "recovery_state", None)]),
        merged_from=_values(getattr(incident, "merged_from", ())),
        split_from=getattr(incident, "split_from", None),
    )
