#!/usr/bin/env python3
"""Validate security metadata and evaluate exact-SHA evidence without scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONTROL_STATES = {
    "not_implemented",
    "implemented",
    "local_tested",
    "hosted_tested",
    "independently_verified",
    "blocked",
    "not_applicable",
    "unknown",
}
EVIDENCE_STATES = {"valid", "missing", "stale", "failed", "partial", "unvalidated", "not_applicable"}
REQUIRED_CONTROL = {
    "id",
    "title",
    "category",
    "description",
    "owner_team",
    "applicability",
    "implementation_state",
    "required_evidence",
    "release_gate",
    "severity_if_missing",
    "verification_method",
    "evidence_freshness_policy",
}
PROVENANCE = {
    "repository",
    "sha",
    "workflow",
    "workflow_run_id",
    "attempt",
    "created_at",
    "tool",
    "checksum",
    "producer",
    "verifier",
    "environment_class",
}


def load(path):
    return yaml.safe_load(Path(path).read_text())


def validate_controls(doc):
    errors = []
    controls = doc.get("controls", [])
    ids = [x.get("id") for x in controls]
    owners = set(doc.get("owners", []))
    errors += [f"duplicate_control:{x}" for x in set(ids) if ids.count(x) > 1]
    for c in controls:
        errors += [f"{c.get('id', 'unknown')}:missing:{k}" for k in REQUIRED_CONTROL - c.keys()]
        if c.get("owner_team") not in owners:
            errors.append(f"{c.get('id')}:unknown_owner")
        if c.get("implementation_state") not in CONTROL_STATES:
            errors.append(f"{c.get('id')}:invalid_state")
        if not c.get("required_evidence"):
            errors.append(f"{c.get('id')}:missing_required_evidence")
    return errors


def verify_artifact(item, sha, now):
    missing = PROVENANCE - set(item)
    if missing:
        return "unvalidated", "MISSING_PROVENANCE:" + ",".join(sorted(missing)), None
    if item["sha"] != sha:
        return "failed", "WRONG_SHA", None
    if item.get("status") != "valid":
        return "failed", "EVIDENCE_FAILED", None
    try:
        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        age = (now - created).total_seconds() / 86400
    except Exception:
        return "unvalidated", "INVALID_TIMESTAMP", None
    payload = dict(item)
    supplied = payload.pop("checksum")
    actual = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if supplied != actual:
        return "failed", "CHECKSUM_MISMATCH", age
    return "valid", None, round(age, 2)


def evaluate(controls_doc, registry_doc, artifacts, sha, profile, now=None):
    now = now or datetime.now(timezone.utc)
    errors = validate_controls(controls_doc)
    ids = {c["id"] for c in controls_doc.get("controls", [])}
    for e in registry_doc.get("evidence", []):
        if e.get("control_id") not in ids:
            errors.append(f"unknown_control:{e.get('control_id')}")
        if e.get("status") not in EVIDENCE_STATES:
            errors.append(f"invalid_evidence_state:{e.get('control_id')}")
    by_type = {a.get("evidence_type"): a for a in artifacts}
    rows = []
    rank = {
        "not_implemented": 0,
        "unknown": 0,
        "blocked": 0,
        "implemented": 1,
        "local_tested": 2,
        "hosted_tested": 3,
        "independently_verified": 4,
        "not_applicable": 5,
    }
    required_rank = {"development": 1, "standard": 2, "production": 3}[profile]
    for c in controls_doc.get("controls", []):
        states = []
        ages = []
        reasons = []
        for et in c["required_evidence"]:
            reg = next(
                (e for e in registry_doc["evidence"] if e["control_id"] == c["id"] and e["evidence_type"] == et), None
            )
            if not reg:
                states.append("missing")
                reasons.append("EVIDENCE_DEFINITION_MISSING")
                continue
            artifact = by_type.get(et)
            if not artifact:
                states.append(reg["status"])
                reasons.append("EVIDENCE_MISSING")
                continue
            state, reason, age = verify_artifact(artifact, sha, now)
            states.append(state)
            if reason:
                reasons.append(reason)
            if age is not None:
                ages.append(age)
        ev = (
            "valid"
            if states and all(x == "valid" for x in states)
            else (
                "failed"
                if "failed" in states
                else ("stale" if "stale" in states else ("missing" if "missing" in states else "unvalidated"))
            )
        )
        mandatory = profile in c["applicability"] and (c["release_gate"] or profile == "production")
        blocker = mandatory and (rank.get(c["implementation_state"], 0) < required_rank or ev != "valid")
        rows.append(
            {
                "control_id": c["id"],
                "category": c["category"],
                "state": c["implementation_state"],
                "evidence_state": ev,
                "evidence_age_days": max(ages) if ages else None,
                "owner": c["owner_team"],
                "blocker": blocker,
                "remediation_code": reasons[0] if reasons else "NONE",
                "release_impact": "blocks" if blocker else "none",
            }
        )
    if errors:
        overall = "FAIL"
    elif any(
        r["blocker"] and (r["state"] in {"blocked", "not_implemented"} or r["evidence_state"] == "failed") for r in rows
    ):
        overall = "FAIL"
    elif any(r["blocker"] and r["evidence_state"] in {"missing", "stale", "partial"} for r in rows):
        overall = "INCOMPLETE"
    elif any(r["blocker"] for r in rows):
        overall = "UNVALIDATED"
    else:
        overall = "PASS"
    return {
        "schema_version": "1.0",
        "repository": "Jagadeeshck/DataObs",
        "sha": sha,
        "profile": profile,
        "generated_at": now.isoformat(),
        "overall_state": overall,
        "validation_errors": errors,
        "controls": rows,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controls", default="docs/security/security-controls.yaml")
    p.add_argument("--registry", default="docs/security/security-evidence-registry.yaml")
    p.add_argument("--artifacts", type=Path)
    p.add_argument("--sha", required=True)
    p.add_argument("--profile", choices=["development", "standard", "production"], default="production")
    p.add_argument("--output", type=Path, default=Path("security-posture-report.json"))
    a = p.parse_args()
    artifacts = json.loads(a.artifacts.read_text()).get("evidence", []) if a.artifacts and a.artifacts.exists() else []
    report = evaluate(load(a.controls), load(a.registry), artifacts, a.sha, a.profile)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(report["overall_state"])
    return 1 if report["overall_state"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
