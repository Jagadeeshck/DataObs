from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

from .changed_models import detect_changes
from .dbt_test_check import evaluate_run_results
from .drift_check import compare_profiles
from .models import ChangeGatePolicy, GateMode, utc_now
from .repository import evaluation_id

RISK_WEIGHTS = {
    "schema_change_severity": 0.20,
    "data_drift": 0.25,
    "dbt_test_failure": 0.25,
    "contract_breakage": 0.20,
    "critical_downstream_assets": 0.10,
}


def evaluate(
    *,
    tenant_id: str,
    environment: str,
    repository: str,
    project_id: str,
    pr_id: str,
    base_sha: str,
    head_sha: str,
    base_manifest: dict,
    head_manifest: dict,
    policy: ChangeGatePolicy,
    run_results: dict | None = None,
    baseline_profile: dict | None = None,
    branch_profile: dict | None = None,
) -> dict:
    if not tenant_id or not environment:
        raise ValueError("authenticated tenant and environment are required")
    changes = detect_changes(base_manifest, head_manifest)
    checks = []
    breaking = any(x["change_type"] == "removed" for x in changes)
    checks.append(
        _check(
            "schema_change",
            "failed" if breaking else "passed",
            0.95,
            ["model_removed"] if breaking else ["schema_change_bounded"],
            {"changes": changes},
        )
    )
    tests = evaluate_run_results(run_results)
    checks.append(
        _check(
            "dbt_tests",
            tests["status"],
            1.0 if run_results else 0.0,
            ["dbt_tests_unavailable"] if run_results is None else ["dbt_tests_evaluated"],
            tests,
            tests["evidence_status"],
        )
    )
    drift = []
    if baseline_profile is not None and branch_profile is not None:
        drift = compare_profiles(baseline_profile, branch_profile, policy.drift_thresholds)
        drift_status = (
            "failed"
            if any(x["status"] == "failed" for x in drift)
            else "warning" if any(x["status"] == "warning" for x in drift) else "passed"
        )
        checks.append(_check("data_drift", drift_status, 1.0, ["aggregate_profiles_compared"], {"comparisons": drift}))
    else:
        checks.append(_check("data_drift", "unknown", 0.0, ["profile_evidence_missing"], {}, "missing"))
    # Contract and lineage are explicit unknowns until their canonical adapters supply evidence.
    checks += [
        _check("contract_compatibility", "unknown", 0.0, ["contract_evidence_missing"], {}, "missing"),
        _check("impact_lineage", "unknown", 0.0, ["lineage_evidence_missing"], {}, "missing"),
    ]
    evidence = {
        "dbt_tests": run_results is not None,
        "branch_profile": branch_profile is not None,
        "baseline_profile": baseline_profile is not None,
        "contract": False,
        "lineage": False,
    }
    missing = sorted(x for x in policy.required_evidence if not evidence.get(x, False))
    blocking = [c for c in checks if c["status"] == "failed"]
    warnings = [c for c in checks if c["status"] == "warning"]
    status = (
        "partial"
        if missing
        else (
            "failed"
            if blocking and policy.gate_mode == GateMode.ENFORCED
            else "warning" if blocking or warnings else "passed"
        )
    )
    components = {
        "schema_change_severity": 1.0 if breaking else 0.0,
        "data_drift": max((x["drift_score"] for x in drift), default=None),
        "dbt_test_failure": (
            (tests.get("failed", 0) + tests.get("error", 0)) / max(1, tests["total"]) if run_results else None
        ),
        "contract_breakage": None,
        "critical_downstream_assets": None,
    }
    available = {k: v for k, v in components.items() if v is not None}
    total = sum(RISK_WEIGHTS[k] for k in available)
    normalized = {k: RISK_WEIGHTS[k] / total for k in available} if total else {}
    risk = round(100 * sum(available[k] * normalized[k] for k in available), 2) if available else None
    confidence = round(sum(c["confidence"] for c in checks) / len(checks), 3)
    eid = evaluation_id(tenant_id, environment, repository, project_id, pr_id, base_sha, head_sha, policy.fingerprint())
    return {
        "evaluation_id": eid,
        "tenant_id": tenant_id,
        "environment": environment,
        "repository": repository,
        "project_id": project_id,
        "pull_request_number": pr_id,
        "base_commit_sha": base_sha,
        "head_commit_sha": head_sha,
        "status": status,
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "changed_model_count": len(changes),
        "changed_models": changes,
        "checks": checks,
        "overall_risk": {
            "risk_score": risk,
            "components": components,
            "available_components": sorted(available),
            "normalized_weights": normalized,
            "formula": "100 * weighted mean of available bounded components",
        },
        "confidence": confidence,
        "blocking_reasons": [r for c in blocking for r in c["reason_codes"]],
        "warning_reasons": [r for c in warnings for r in c["reason_codes"]],
        "unknown_reasons": missing,
        "evidence_status": "partial" if missing else "available",
        "evidence_refs": [],
        "started_at": utc_now(),
        "completed_at": utc_now(),
        "created_at": utc_now(),
        "schema_version": "v1",
    }


def _check(kind, status, confidence, reasons, metrics, evidence="available"):
    digest = sha256(json.dumps([kind, reasons, metrics], sort_keys=True, default=str).encode()).hexdigest()[:20]
    return {
        "check_id": f"cgc_{digest}",
        "check_type": kind,
        "status": status,
        "severity": (
            "high"
            if status == "failed"
            else "medium" if status == "warning" else "unknown" if status == "unknown" else "low"
        ),
        "confidence": confidence,
        "summary": "; ".join(reasons),
        "reason_codes": reasons,
        "changed_entities": [],
        "affected_entities": [],
        "metrics": metrics,
        "evidence_status": evidence,
        "evidence_refs": [],
        "started_at": utc_now(),
        "completed_at": utc_now(),
    }
