from datetime import datetime, timezone

import pytest

from scripts.release.first_supported_platform import (
    evaluate_profile,
    verify_artifacts,
    verify_evidence,
    verify_supply_chain,
)
from scripts.release.release_decision import decide

SHA = "a" * 40
NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def evidence(**updates):
    value = {
        "evidence_category": "hosted",
        "artifact_name": "run",
        "exact_sha": SHA,
        "status": "pass",
        "expires_at": "2026-09-01T00:00:00Z",
        "checksum": "sha256:" + "0" * 64,
    }
    value.update(updates)
    return value


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"exact_sha": "b" * 40}, "hosted:WRONG_SHA"),
        ({"expires_at": "2026-08-01T00:00:00Z"}, "hosted:STALE_EVIDENCE"),
        ({"evidence_class": "FUNCTIONAL_SIMULATION", "hosted_required": True}, "hosted:SIMULATION_NOT_HOSTED"),
        ({"status": "fail"}, "hosted:REQUIRED_SCENARIO_NOT_PASSING"),
    ],
)
def test_evidence_rejections(updates, reason):
    assert reason in verify_evidence([evidence(**updates)], SHA, NOW)


def test_duplicate_and_missing_evidence_are_rejected():
    item = evidence(status="pending", checksum=None)
    assert "hosted:DUPLICATE_EVIDENCE" in verify_evidence([item, item], SHA, NOW)
    assert verify_evidence([], SHA, NOW) == ["inventory:MISSING_EVIDENCE"]


def test_checksum_mismatch(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.write_text("changed")
    failures = verify_evidence([evidence(path=str(artifact))], SHA, NOW)
    assert "hosted:CHECKSUM_MISMATCH" in failures


def gates(result="PASS", category="security"):
    return [{"id": category, "category": category, "mandatory_profiles": ["development"], "result": result}]


def test_eligible_profile_is_promoted():
    assert evaluate_profile({"candidate_profile": "development", "ha_profile": "development"}, gates()) == "eligible"


@pytest.mark.parametrize("category", ["security", "tenant-isolation", "restore"])
def test_failed_mandatory_profile_gate_prevents_promotion(category):
    assert (
        evaluate_profile({"candidate_profile": "development", "ha_profile": "development"}, gates("FAIL", category))
        == "incomplete"
    )


def test_unsupported_ha_is_rejected_after_passing_gates():
    assert evaluate_profile({"candidate_profile": "development", "ha_profile": "unsupported"}, gates()) == "ineligible"


def manifest():
    return {
        "git_sha": SHA,
        "chart_digest": "sha256:" + "1" * 64,
        "terminal_migration": "0030_x",
        "images": [{"repository": "api", "tag": "rc1", "digest": "sha256:" + "2" * 64, "build_sha": SHA}],
    }


def test_mutable_image_and_build_mismatch_rejected():
    value = manifest()
    value["images"][0].update(tag="latest", build_sha="b" * 40)
    result = verify_artifacts(value)
    assert "MUTABLE_OR_MISSING_IMAGE_DIGEST" in result and "IMAGE_BUILD_SHA_MISMATCH" in result


def test_chart_and_install_substitution_rejected():
    value = manifest()
    value["chart_digest"] = "wrong"
    installed = {
        "chart_digest": "different",
        "git_sha": SHA,
        "terminal_migration": "wrong",
        "image_digests": {},
        "readiness": "fail",
        "authentication": "fail",
        "tenant_isolation": "fail",
    }
    result = verify_artifacts(value, installed)
    assert "INVALID_CHART_DIGEST" in result
    assert "INSTALLED_CHART_DIGEST_MISMATCH" in result
    assert "INSTALLED_TERMINAL_MIGRATION_MISMATCH" in result
    assert "INSTALLED_IMAGE_DIGEST_MISMATCH" in result
    assert "INSTALL_READINESS_FAILED" in result
    assert "INSTALL_AUTHENTICATION_FAILED" in result
    assert "INSTALL_TENANT_ISOLATION_FAILED" in result


def test_supply_chain_failures_are_explicit():
    report = {
        "sbom": "missing",
        "provenance": "invalid",
        "signature": "invalid",
        "critical_vulnerabilities": 1,
        "license_policy": "unknown",
        "waivers": [{"expires_at": "2026-01-01T00:00:00Z"}],
    }
    result = verify_supply_chain(report, NOW)
    assert set(result) >= {
        "INVALID_OR_MISSING_SBOM",
        "INVALID_OR_MISSING_PROVENANCE",
        "INVALID_OR_MISSING_SIGNATURE",
        "UNWAIVED_HIGH_OR_CRITICAL_VULNERABILITY",
        "EXPIRED_VULNERABILITY_WAIVER",
        "LICENSE_POLICY_FAILED",
    }


def authority_manifest(result="pass"):
    keys = (
        "deployment_certification_result",
        "security_certification_result",
        "tenant_isolation_result",
        "recovery_result",
        "upgrade_rollback_result",
        "independent_verification_result",
        "redaction_status",
        "vulnerability_policy_result",
    )
    return {**{key: result for key in keys}, "capability_artifact_inventory": [{"status": "pass"}]}


def test_missing_gate_is_no_go_and_all_pass_allows_publication():
    failed = authority_manifest()
    failed["recovery_result"] = "pending"
    assert decide(failed, dry_run=False)["state"] == "NO_GO"
    assert decide(authority_manifest(), dry_run=False)["state"] == "APPROVED_FOR_PUBLICATION"


def test_publication_mismatch_is_verification_failed():
    value = authority_manifest()
    value["publication_status"] = "published"
    assert decide(value, dry_run=False)["state"] == "VERIFICATION_FAILED"
