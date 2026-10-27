import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from scripts.release import post_recovery_rebaseline as baseline

SHA = "a" * 40


def test_candidate_rejects_non_exact_sha():
    with pytest.raises(ValueError, match="exact"):
        baseline.validate_candidate("main", "origin/main", "0033_team1_stream_schema_intelligence_runtime")


def test_candidate_rejects_unreachable_and_ambiguous(monkeypatch):
    monkeypatch.setattr(baseline, "git", lambda *args: "b" * 40)
    with pytest.raises(ValueError, match="ambiguous"):
        baseline.validate_candidate(SHA, "origin/main", "0033_team1_stream_schema_intelligence_runtime")


def test_candidate_rejects_wrong_terminal(monkeypatch):
    monkeypatch.setattr(baseline, "git", lambda *args: SHA)
    monkeypatch.setattr(baseline.subprocess, "run", lambda *args, **kwargs: type("R", (), {"returncode": 0})())
    monkeypatch.setattr(
        baseline.subprocess,
        "check_output",
        lambda *args, **kwargs: json.dumps({"terminal_migration": "wrong"}),
    )
    with pytest.raises(ValueError, match="terminal migration"):
        baseline.validate_candidate(SHA, "origin/main", "0033_team1_stream_schema_intelligence_runtime")


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"exact_sha": "b" * 40}, "WRONG_SHA"),
        ({"expires_at": "2020-01-01T00:00:00Z"}, "EXPIRED"),
        ({"mandatory_test_result": "not_run"}, "MANDATORY_TEST_NOT_PASSING"),
    ],
)
def test_verified_evidence_fails_closed(change, reason):
    item = {
        "exact_sha": SHA,
        "verification_state": "VERIFIED",
        "workflow": "workflow.yml",
        "run_id": 1,
        "run_attempt": 1,
        "artifact_id": 2,
        "created_at": "2026-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "checksum": "sha256:" + "0" * 64,
        "mandatory_test_result": "pass",
    }
    item.update(change)
    assert reason in baseline.verify_item(item, SHA, datetime.now(timezone.utc))


def test_missing_manifest_or_test_report_cannot_be_verified():
    item = {"exact_sha": SHA, "verification_state": "VERIFIED", "mandatory_test_result": "pass"}
    assert "MISSING_VERIFICATION_METADATA" in baseline.verify_item(item, SHA, datetime.now(timezone.utc))


def test_checksum_mismatch_is_rejected(tmp_path):
    artifact = tmp_path / "artifact.zip"
    artifact.write_bytes(b"changed")
    item = {
        "exact_sha": SHA,
        "verification_state": "VERIFIED",
        "workflow": "workflow.yml",
        "run_id": 1,
        "run_attempt": 1,
        "artifact_id": 2,
        "created_at": "2026-01-01T00:00:00Z",
        "checksum": "sha256:" + "0" * 64,
        "local_path": str(artifact),
        "mandatory_test_result": "pass",
    }
    assert "CHECKSUM_MISMATCH" in baseline.verify_item(item, SHA, datetime.now(timezone.utc))


def test_cross_team_blocker_prevents_platform_promotion():
    index = {
        "evidence": [
            {
                "artifact": capability,
                "capability": capability,
                "exact_sha": SHA,
                "verification_state": "VERIFIED",
                "workflow": "w",
                "run_id": 1,
                "run_attempt": 1,
                "artifact_id": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "checksum": "sha256:" + "0" * 64,
                "mandatory_test_result": "pass",
            }
            for capability in baseline.MANDATORY_CAPABILITIES
        ]
    }
    gates = baseline.derive_gates(
        index,
        [{"gate": "kafka-stream-runtime", "state": "OPEN", "owner_team": "Team 1"}],
        SHA,
    )
    assert next(g for g in gates if g["id"] == "kafka-stream-runtime")["result"] == "FAIL"
    assert baseline.supported_platform(gates)["supported"] == []


def test_hosted_iam_and_local_tenant_tests_do_not_satisfy_hosted_gates():
    index = {
        "evidence": [
            {"artifact": "iam", "capability": "iam-rbac", "exact_sha": SHA, "verification_state": "VERIFIED"},
            {
                "artifact": "tenant-unit",
                "capability": "tenant-unit",
                "exact_sha": SHA,
                "verification_state": "VERIFIED",
            },
        ]
    }
    gates = baseline.derive_gates(index, [], SHA)
    assert next(g for g in gates if g["id"] == "hosted-oidc")["result"] == "PENDING"
    assert next(g for g in gates if g["id"] == "hosted-tenant-isolation")["result"] == "PENDING"


def test_foundation_contexts_are_unique_and_reusable_cannot_masquerade():
    root = Path(__file__).parents[2]
    foundation = yaml.safe_load((root / ".github/workflows/team-delivery-foundation.yml").read_text())
    assert {"foundation-backend", "foundation-console"} <= foundation["jobs"].keys()
    assert "backend" not in foundation["jobs"] and "console" not in foundation["jobs"]
    backend = yaml.safe_load((root / ".github/workflows/reusable-backend-validation.yml").read_text())
    assert backend["name"] == "Reusable backend validation"
