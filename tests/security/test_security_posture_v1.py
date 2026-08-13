import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from scripts.release.release_decision import decide
from scripts.security.evaluate_security_posture import evaluate, validate_controls, verify_artifact
from scripts.security.validate_security_exceptions import validate as validate_exceptions
from scripts.security.validate_sensitive_outputs import inspect as inspect_sensitive
from scripts.security.validate_threat_models import validate as validate_threat_models

ROOT = Path(__file__).parents[2]


def controls():
    return yaml.safe_load((ROOT / "docs/security/security-controls.yaml").read_text())


def registry():
    return yaml.safe_load((ROOT / "docs/security/security-evidence-registry.yaml").read_text())


def artifact(sha="a" * 40, status="valid", created=None):
    x = {
        "evidence_type": "unit-test",
        "repository": "Jagadeeshck/DataObs",
        "sha": sha,
        "workflow": "ci",
        "workflow_run_id": "1",
        "attempt": 1,
        "created_at": created or datetime.now(timezone.utc).isoformat(),
        "tool": "pytest/8",
        "producer": "Security Team",
        "verifier": "Security Team",
        "environment_class": "local",
        "status": status,
    }
    x["checksum"] = hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return x


def test_control_validation_rejects_duplicate_unknown_owner_missing_evidence_and_state():
    d = controls()
    d["controls"].append(copy.deepcopy(d["controls"][0]))
    d["controls"][0]["owner_team"] = "nobody"
    d["controls"][0]["required_evidence"] = []
    d["controls"][0]["implementation_state"] = "verified-ish"
    e = validate_controls(d)
    assert any("duplicate_control" in x for x in e)
    assert any("unknown_owner" in x for x in e)
    assert any("missing_required_evidence" in x for x in e)
    assert any("invalid_state" in x for x in e)


def test_evidence_accepts_valid_and_rejects_wrong_sha_missing_checksum_failed():
    now = datetime.now(timezone.utc)
    a = artifact()
    assert verify_artifact(a, "a" * 40, now)[0] == "valid"
    assert verify_artifact(a, "b" * 40, now)[1] == "WRONG_SHA"
    b = dict(a)
    b.pop("checksum")
    assert verify_artifact(b, "a" * 40, now)[0] == "unvalidated"
    c = artifact(status="failed")
    assert verify_artifact(c, "a" * 40, now)[1] == "EVIDENCE_FAILED"


def test_stale_registry_evidence_is_not_pass():
    d = registry()
    d["evidence"][0]["status"] = "stale"
    r = evaluate(controls(), d, [], "a" * 40, "production")
    assert r["overall_state"] != "PASS"
    assert any(x["evidence_state"] == "stale" for x in r["controls"])


def test_threat_model_missing_document_stale_review_unknown_control():
    d = {
        "review_maximum_age_days": 1,
        "threat_models": [
            {
                "threat_model_id": "x",
                "document": "missing",
                "status": "current",
                "last_reviewed": "2020-01-01",
                "relevant_controls": ["SEC-NOPE"],
            }
        ],
    }
    e = validate_threat_models(d, controls(), ROOT)
    assert {"x:missing_document", "x:stale_review", "x:unknown_control:SEC-NOPE"} <= set(e)


def test_exception_fail_closed_cases():
    base = {
        "exception_id": "x",
        "control_id": "SEC-AUTHN-001",
        "scope": "production:tenant-a",
        "owner": "Security Team",
        "approval_reference": "SEC-1",
        "compensating_controls": ["monitor"],
        "expiry": "2020-01-01T00:00:00Z",
    }
    e = validate_exceptions(controls(), {"exceptions": [base]})
    assert "x:expired" in e
    for field, value, code in [
        ("control_id", "NOPE", "unknown_control"),
        ("scope", "production:*", "wildcard_production_scope"),
        ("approval_reference", "", "missing_approval_reference"),
    ]:
        x = dict(base)
        x["expiry"] = "2099-01-01T00:00:00Z"
        x[field] = value
        assert any(code in y for y in validate_exceptions(controls(), {"exceptions": [x]}))


def test_secret_detection_never_returns_secret(tmp_path):
    secret = "Bearer abcdefghijklmnopqrstuvwxyz"
    p = tmp_path / "x"
    p.write_text("Authorization: " + secret)
    f = inspect_sensitive([p])
    assert f and secret not in json.dumps(f)
    q = tmp_path / "safe"
    q.write_text("token_reference: secret/dataobs")
    assert inspect_sensitive([q]) == []


def test_implemented_without_evidence_and_local_are_not_hosted():
    r = evaluate(controls(), registry(), [], "a" * 40, "production")
    assert r["overall_state"] in {"INCOMPLETE", "UNVALIDATED"}
    assert any(x["state"] == "implemented" and x["evidence_state"] != "valid" for x in r["controls"])
    assert any(x["state"] == "local_tested" and x["blocker"] for x in r["controls"])


def test_critical_failed_control_fails():
    d = controls()
    d["controls"][0]["implementation_state"] = "blocked"
    reg = registry()
    reg["evidence"][0]["status"] = "failed"
    r = evaluate(d, reg, [], "a" * 40, "production")
    assert r["overall_state"] == "FAIL"


def test_release_authority_consumes_security_gate():
    m = {
        k: "pass"
        for k in (
            "deployment_certification_result",
            "security_certification_result",
            "tenant_isolation_result",
            "recovery_result",
            "upgrade_rollback_result",
            "independent_verification_result",
            "redaction_status",
            "vulnerability_policy_result",
        )
    }
    m["capability_artifact_inventory"] = []
    assert decide(m, dry_run=False, security_gate={"state": "FAIL"})["state"] == "NO_GO"
    assert decide(m, dry_run=False, security_gate={"state": "INCOMPLETE"})["state"] == "NO_GO"
    assert decide(m, dry_run=False, security_gate={"state": "PASS"})["state"] == "APPROVED_FOR_PUBLICATION"


def test_vulnerability_blocking_and_waiver_expiry_semantics():
    policy = yaml.safe_load((ROOT / "docs/security/vulnerability-policy.yaml").read_text())
    assert policy["severities"]["critical"]["state"] == "blocking"
    assert policy["severities"]["critical"]["waiver_required"]
    schema = json.loads((ROOT / "docs/security/vulnerability-exceptions.schema.json").read_text())
    assert "expires_at" in schema["items"]["required"]
