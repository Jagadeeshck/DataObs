from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .models import ContractEvaluation, ContractVersion, DataContract, EnforcementMode, Evidence, Violation
from .schema_rules import type_compatibility


def _violation(
    contract: DataContract,
    version: ContractVersion,
    requirement: str,
    category: str,
    field: str | None,
    expected: Any,
    observed: Any,
    reason: str,
    severity: str = "high",
) -> Violation:
    key = f"{contract.tenant_id}|{contract.environment}|{contract.contract_id}|{version.version}|{requirement}"
    return Violation(
        hashlib.sha256(key.encode()).hexdigest(),
        requirement,
        category,
        field,
        expected,
        observed,
        severity,
        "direct",
        reason,
    )


def evaluate_contract(
    contract: DataContract, version: ContractVersion, evidence: Evidence, *, now: datetime | None = None
) -> ContractEvaluation:
    now = now or datetime.now(timezone.utc)
    if contract.enforcement_mode == EnforcementMode.DISABLED:
        return _result(contract, version, evidence, now, "disabled", [], {}, [], [])
    violations: list[Violation] = []
    unavailable: list[str] = []
    stale: list[str] = []
    components: dict[str, float | None] = {}

    if evidence.schema_columns is None:
        unavailable.append("schema")
        components["schema"] = None
    else:
        observed = {str(c.get("name", "")).lower(): c for c in evidence.schema_columns}
        scores: list[float] = []
        contracted = {r.name.lower() for r in version.columns}
        for rule in version.columns:
            item = observed.get(rule.name.lower())
            if item is None:
                if rule.required:
                    violations.append(
                        _violation(
                            contract,
                            version,
                            f"schema:{rule.name}",
                            "schema",
                            rule.name,
                            "required field",
                            None,
                            "missing_required_field",
                        )
                    )
                    scores.append(0)
                continue
            compatibility = type_compatibility(rule.expected_type, item.get("type"), rule.compatible_types)
            if compatibility in {"incompatible", "narrowing"}:
                violations.append(
                    _violation(
                        contract,
                        version,
                        f"schema:{rule.name}:type",
                        "compatibility",
                        rule.name,
                        rule.expected_type,
                        item.get("type"),
                        "type_mismatch",
                    )
                )
                scores.append(0)
            elif compatibility == "unknown":
                unavailable.append(f"schema:{rule.name}:type")
            else:
                scores.append(1)
            if rule.nullable is False and item.get("nullable") is True:
                violations.append(
                    _violation(
                        contract,
                        version,
                        f"schema:{rule.name}:nullable",
                        "schema",
                        rule.name,
                        False,
                        True,
                        "nullability_mismatch",
                    )
                )
                scores.append(0)
        if version.compatibility.value == "strict":
            for name in observed.keys() - contracted:
                violations.append(
                    _violation(
                        contract,
                        version,
                        f"schema:{name}:unexpected",
                        "schema",
                        name,
                        "no unexpected fields",
                        name,
                        "unexpected_field",
                        "medium",
                    )
                )
                scores.append(0)
        components["schema"] = sum(scores) / len(scores) if scores else 1.0

    for requirement in version.quality_requirements:
        item = evidence.monitor_states.get(requirement.monitor_id)
        key = f"quality:{requirement.monitor_id}"
        if not item or item.get("state") in {None, "disabled", "unknown"}:
            unavailable.append(key)
            continue
        if item.get("suppressed"):
            stale.append(key + ":suppressed")
        if item["state"] != requirement.required_state:
            violations.append(
                _violation(
                    contract,
                    version,
                    key,
                    "quality",
                    None,
                    requirement.required_state,
                    item["state"],
                    "monitor_state_breach",
                    requirement.severity,
                )
            )
    if version.quality_requirements:
        available = len(version.quality_requirements) - sum(
            x.startswith("quality:") and not x.endswith(":suppressed") for x in unavailable
        )
        failed = sum(v.category == "quality" for v in violations)
        components["quality"] = max(0.0, (available - failed) / available) if available else None

    if version.freshness_max_age_seconds is not None:
        if evidence.freshness_age_seconds is None:
            unavailable.append("freshness")
            components["freshness"] = None
        else:
            limit = version.freshness_max_age_seconds + version.freshness_grace_seconds
            components["freshness"] = 1.0 if evidence.freshness_age_seconds <= limit else 0.0
            if evidence.freshness_age_seconds > limit:
                violations.append(
                    _violation(
                        contract,
                        version,
                        "freshness",
                        "freshness",
                        None,
                        {"maximum_age_seconds": limit},
                        {"age_seconds": evidence.freshness_age_seconds},
                        "freshness_age_exceeded",
                    )
                )

    if version.volume_min is not None or version.volume_max is not None:
        if evidence.record_count is None:
            unavailable.append("volume")
            components["volume"] = None
        else:
            ok = (version.volume_min is None or evidence.record_count >= version.volume_min) and (
                version.volume_max is None or evidence.record_count <= version.volume_max
            )
            components["volume"] = float(ok)
            if not ok:
                violations.append(
                    _violation(
                        contract,
                        version,
                        "volume",
                        "volume",
                        None,
                        {"min": version.volume_min, "max": version.volume_max},
                        {"record_count": evidence.record_count},
                        "volume_out_of_bounds",
                    )
                )

    if version.metadata_requirements:
        missing = [x for x in version.metadata_requirements if not evidence.asset_metadata.get(x)]
        components["metadata"] = (len(version.metadata_requirements) - len(missing)) / len(
            version.metadata_requirements
        )
        violations.extend(
            _violation(
                contract,
                version,
                f"metadata:{x}",
                "metadata",
                None,
                "present",
                None,
                "required_metadata_missing",
                "medium",
            )
            for x in missing
        )

    available = [x for x in components.values() if x is not None]
    confidence = len(available) / max(1, len(components))
    critical = any(v.severity in {"critical", "high"} and v.directness == "direct" for v in violations)
    if violations:
        state = (
            "warning" if contract.enforcement_mode in {EnforcementMode.OBSERVE, EnforcementMode.WARN} else "breaching"
        )
    elif stale:
        state = "stale"
    elif not available or confidence < 0.5:
        state = "unknown" if components else "no_data"
    else:
        state = "compliant"
    if critical and contract.enforcement_mode == EnforcementMode.ENFORCE:
        state = "breaching"
    return _result(contract, version, evidence, now, state, violations, components, unavailable, stale)


def _result(
    contract: DataContract,
    version: ContractVersion,
    evidence: Evidence,
    now: datetime,
    state: str,
    violations: list[Violation],
    components: dict[str, float | None],
    unavailable: list[str],
    stale: list[str],
) -> ContractEvaluation:
    available = [v for v in components.values() if v is not None]
    score = sum(available) / len(available) if available else None
    confidence = len(available) / max(1, len(components))
    evaluation_id = hashlib.sha256(
        f"{contract.contract_id}|{version.version}|{evidence.observed_at.isoformat()}|{version.fingerprint}".encode()
    ).hexdigest()
    return ContractEvaluation(
        evaluation_id,
        contract.contract_id,
        version.version,
        contract.asset_id,
        now,
        evidence.observed_at,
        state,
        contract.enforcement_mode.value,
        score,
        confidence,
        components,
        "equal weights normalized across available components; unavailable excluded",
        tuple(violations),
        tuple(unavailable),
        tuple(stale),
        evidence.references,
        version.fingerprint,
        tuple(sorted({v.reason_code for v in violations})),
    )
