from __future__ import annotations

import pytest

from scripts.release.verify_beta_candidate import validate_evidence, verify_entry

SHA = "a" * 40
ENTRY = {
    "capability_id": "platform.security",
    "owning_team": "Team 0",
    "workflow": "beta-1-release-candidate.yml",
    "artifact": "team-0-evidence",
    "required_conclusion": "success",
    "mandatory_for_beta": True,
    "evidence_schema_version": "1.0",
    "expected_elasticsearch_version": "9.4.2",
}


def run(**changes):
    value = {
        "id": 7,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "path": ".github/workflows/beta-1-release-candidate.yml",
        "repository": {"full_name": "owner/repo"},
    }
    value.update(changes)
    return value


def evidence(**changes):
    value = {
        "schema_version": "1.0",
        "producer_sha": SHA,
        "terminal_migration": "0021_lineage_analysis_explorer",
        "elasticsearch_version": "9.4.2",
        "test_summaries": [{"category": "security", "passed": 10}],
        "tool_versions": {"python": "3.13"},
        "workflow_file": "beta-1-release-candidate.yml",
        "workflow_run_id": "7",
        "workflow_run_attempt": "1",
        "event": "workflow_dispatch",
        "redaction_status": "pass",
        "status": "pass",
    }
    value.update(changes)
    return value


def verify(*, runs=None, artifacts=None, payload=None, entry=None):
    return verify_entry(
        entry or ENTRY,
        repository="owner/repo",
        target_sha=SHA,
        terminal="0021_lineage_analysis_explorer",
        runs=[run()] if runs is None else runs,
        artifacts=[{"name": "team-0-evidence", "workflow_run": {"id": 7}}] if artifacts is None else artifacts,
        load_evidence=lambda _: evidence() if payload is None else payload,
    )


def test_accepts_exact_successful_unambiguous_evidence():
    assert verify()["status"] == "pass"


@pytest.mark.parametrize(
    ("runs", "message"),
    [
        ([], "missing qualifying"),
        ([run(conclusion="failure")], "conclusion is failure"),
        ([run(conclusion="cancelled")], "conclusion is cancelled"),
        ([run(), run(id=8)], "multiple ambiguous"),
        ([run(head_sha="b" * 40)], "missing qualifying"),
    ],
)
def test_rejects_missing_failed_cancelled_ambiguous_or_wrong_sha(runs, message):
    result = verify(runs=runs)
    assert result["status"] == "fail"
    assert any(message in error for error in result["errors"])


def test_rejects_missing_or_wrong_artifact_name():
    assert "artifact" in verify(artifacts=[])["errors"][0]
    wrong = [{"name": "wrong", "workflow_run": {"id": 7}}]
    assert verify(artifacts=wrong)["status"] == "fail"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"producer_sha": "b" * 40}, "producer SHA"),
        ({"terminal_migration": "0020_old"}, "terminal migration"),
        ({"schema_version": "2.0"}, "unsupported evidence schema"),
        ({"test_summaries": []}, "test summary"),
    ],
)
def test_evidence_schema_sha_migration_and_summary_are_enforced(changes, message):
    result = verify(payload=evidence(**changes))
    assert result["status"] == "fail"
    assert any(message in error for error in result["errors"])


def test_optional_capability_failure_is_pending_not_passing():
    optional = {**ENTRY, "mandatory_for_beta": False}
    assert verify(runs=[], entry=optional)["status"] == "optional_failed"


def test_invalid_evidence_object_is_reported_without_token_or_payload_content():
    result = verify(payload={})
    assert result["status"] == "fail"
    assert validate_evidence(ENTRY, {}, SHA, "0021_lineage_analysis_explorer")
