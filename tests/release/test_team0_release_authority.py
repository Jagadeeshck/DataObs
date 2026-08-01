from __future__ import annotations

from pathlib import Path

import yaml

from scripts.release.release_decision import decide
from scripts.release.validate_team0_naming import violations
from scripts.release.verify_beta_candidate import verify_entry

ROOT = Path(__file__).parents[2]
SHA = "a" * 40


def test_active_surfaces_have_canonical_team_zero_names() -> None:
    assert violations(ROOT) == []


def test_workflow_separates_read_only_certification_from_oidc_publication() -> None:
    workflow = (ROOT / ".github/workflows/team-0-release-candidate.yml").read_text()
    assert "permissions: {contents: read, actions: read}" in workflow
    assert "if: ${{ !inputs.dry_run }}" in workflow
    assert "environment: production-release" in workflow
    assert workflow.count("id-token: write") == 1
    assert workflow.index("helm lint") < workflow.index("docker/login-action")


def test_release_decision_fails_pending_and_only_certifies_complete_dry_run() -> None:
    manifest = {
        key: "pass"
        for key in (
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
    manifest["capability_artifact_inventory"] = [{"mandatory": True, "status": "pending"}]
    assert decide(manifest, dry_run=True)["state"] == "NO_GO"
    manifest["capability_artifact_inventory"][0]["status"] = "pass"
    assert decide(manifest, dry_run=True)["state"] == "DRY_RUN_CERTIFIED"


def test_explicit_legacy_alias_is_accepted_but_mixed_nonidentical_is_ambiguous() -> None:
    entry = {
        "capability_id": "team0.proof",
        "owning_team": "Team 0",
        "workflow": "proof.yml",
        "artifact": "team-0-proof",
        "required_conclusion": "success",
        "mandatory_for_beta": True,
        "evidence_schema_version": "1.0",
        "expected_elasticsearch_version": "9.4.2",
        "accepted_events": ["workflow_dispatch"],
        "required_test_categories": ["security"],
    }
    run = {
        "id": 1,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "path": ".github/workflows/proof.yml",
        "repository": {"full_name": "o/r"},
    }
    base = {
        "schema_version": "1.0",
        "producer_sha": SHA,
        "terminal_migration": "m",
        "elasticsearch_version": "9.4.2",
        "test_summaries": [{"category": "security"}],
        "tool_versions": {},
        "workflow_file": "proof.yml",
        "workflow_run_id": "1",
        "workflow_run_attempt": "1",
        "event": "workflow_dispatch",
        "redaction_status": "pass",
        "status": "pass",
    }
    aliases = {"team-0-proof": {"legacy_names": ["team-6-proof"], "allow_byte_identical_coexistence": True}}
    artifacts = [
        {"name": "team-0-proof", "id": 1, "workflow_run": {"id": 1}},
        {"name": "team-6-proof", "id": 2, "workflow_run": {"id": 1}},
    ]
    result = verify_entry(
        entry,
        repository="o/r",
        target_sha=SHA,
        terminal="m",
        runs=[run],
        artifacts=artifacts,
        load_evidence=lambda item: {**base, "variant": item["id"]},
        compatibility_aliases=aliases,
    )
    assert result["status"] == "fail"
    assert "ambiguous" in result["errors"][0]


def test_manifest_aliases_are_explicit_and_bounded_to_schema_one() -> None:
    manifest = yaml.safe_load((ROOT / "docs/release/beta-1-certification-manifest.yaml").read_text())
    assert all(name.startswith("team-0-") for name in manifest["compatibility_aliases"])
    assert all(contract["schema_versions"] == ["1.0"] for contract in manifest["compatibility_aliases"].values())
