from datetime import datetime, timezone

import pytest

from packages.elastic_store.manifest import (
    DATA_PRODUCT_EVIDENCE_OWNERS,
    DATA_PRODUCT_EVIDENCE_PROFILES,
    DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS,
    DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE,
    DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES,
    DATA_PRODUCT_RECONCILIATION_EVIDENCE,
    DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE,
    data_product_evidence_inventory,
)
from scripts.certification.assemble_data_product_evidence import assemble
from scripts.certification.data_product_evidence import write_scenario
from scripts.certification.verify_artifacts import _manifest_provenance_errors


def test_scenario_writer_records_the_executing_test(tmp_path):
    now = datetime.now(timezone.utc)
    target = write_scenario(
        tmp_path,
        filename="migration-clean-install.json",
        scenario="clean install",
        elasticsearch_version="9.4.2",
        test_names=["test_scenario_writer_records_the_executing_test"],
        assertion_summary=["latest migration exists"],
        redacted_references=[],
        started_at=now,
        completed_at=now,
        result="passed",
    )
    assert '"schema_version": "1.0"' in target.read_text()


def test_scenario_writer_rejects_placeholder_evidence(tmp_path):
    with pytest.raises(ValueError, match="non-empty"):
        write_scenario(
            tmp_path,
            filename="empty.json",
            scenario="",
            elasticsearch_version="9.4.2",
            test_names=[],
            assertion_summary=[],
            redacted_references=[],
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:00:00Z",
            result="passed",
        )


def test_evidence_ownership_is_explicit_complete_and_unique():
    owned = [name for artifacts in DATA_PRODUCT_EVIDENCE_OWNERS.values() for name in artifacts]
    assert len(owned) == len(set(owned))
    assert set(owned) == set(DATA_PRODUCT_RECONCILIATION_EVIDENCE)
    assert DATA_PRODUCT_EVIDENCE_OWNERS["contracts"] == ("contracts.xml",)
    assert DATA_PRODUCT_EVIDENCE_OWNERS["unit"] == ("unit.xml",)


def test_foundation_and_full_profiles_have_explicit_unique_ownership():
    assert set(DATA_PRODUCT_EVIDENCE_PROFILES) == {
        "data-product-runtime-foundation",
        "data-product-reconciliation-full",
    }
    owned = [name for values in DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS.values() for name in values]
    assert len(owned) == len(set(owned))
    assert set(owned) == set(DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE)
    assert set(DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE) < set(DATA_PRODUCT_RECONCILIATION_EVIDENCE)
    assert DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS["elasticsearch"][0] == "migrations.xml"
    assert set(DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE) == {
        name for values in DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS.values() for name in values if name.endswith(".xml")
    }
    assert set(DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES) == set(DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE)
    assert DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES["unit.xml"]["allow_skips"] is True
    assert all(
        not policy["allow_skips"]
        for name, policy in DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES.items()
        if name != "unit.xml"
    )
    with pytest.raises(ValueError, match="unknown"):
        data_product_evidence_inventory("inferred-from-files")


def test_scenario_writer_rejects_naive_time_and_unowned_filename(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        write_scenario(
            tmp_path,
            filename="mapping-contract.json",
            scenario="mapping",
            elasticsearch_version="9.4.2",
            test_names=["test"],
            assertion_summary=["mapped"],
            redacted_references=[],
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:01",
            result="passed",
        )


def test_retained_manifest_commit_must_be_a_full_sha(monkeypatch):
    errors = _manifest_provenance_errors(
        {
            "certification_profile": "data-product-runtime-foundation",
            "workflow_event": "pull_request",
            "full_reconciliation_certified": False,
            "release_readiness": "blocked",
            "capabilities": {},
            "repository": "Jagadeeshck/DataObs",
            "commit_sha": "dispatch",
            "workflow_run_id": 1,
            "workflow_run_url": "https://github.com/Jagadeeshck/DataObs/actions/runs/1",
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:01Z",
        }
    )
    assert "manifest commit SHA is invalid" in errors
    monkeypatch.setenv("EXPECTED_HOSTED_SHA", "b" * 40)
    valid = {
        "certification_profile": "data-product-runtime-foundation",
        "workflow_event": "pull_request",
        "full_reconciliation_certified": False,
        "release_readiness": "blocked",
        "capabilities": {},
        "repository": "Jagadeeshck/DataObs",
        "commit_sha": "a" * 40,
        "workflow_run_id": 1,
        "workflow_run_url": "https://github.com/Jagadeeshck/DataObs/actions/runs/1",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:00:01Z",
    }
    assert "manifest commit SHA does not match expected hosted SHA" in _manifest_provenance_errors(valid)


def test_assembler_rejects_a_nonempty_retained_directory(tmp_path):
    downloaded, retained = tmp_path / "downloaded", tmp_path / "retained"
    downloaded.mkdir()
    retained.mkdir()
    (retained / "stale.json").write_text("{}")
    with pytest.raises(ValueError, match="begin empty"):
        assemble(downloaded, retained, profile="data-product-runtime-foundation")
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="undeclared"):
        write_scenario(
            tmp_path,
            filename="reservation-only-matrix.json",
            scenario="full only",
            elasticsearch_version="9.4.2",
            test_names=["test"],
            assertion_summary=["no promotion"],
            redacted_references=[],
            started_at=now,
            completed_at=now,
            result="passed",
            profile="data-product-runtime-foundation",
        )
