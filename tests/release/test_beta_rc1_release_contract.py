from __future__ import annotations

import json
from pathlib import Path

from scripts.release.current_terminal_migration import migration_report
from scripts.release.validate_certification_manifest import validate
from scripts.release.verify_integrated_rc import verify

ROOT = Path(__file__).parents[2]


def test_terminal_migration_comes_from_ordered_registry():
    report = migration_report()
    assert report["terminal_migration"] == "0030_team1_multi_broker_messaging_runtime"
    assert report["migration_count"] == 30
    assert report["ordered_migration_ids"][-2:] == [
        "0029_team2_data_intelligence_reconciliation",
        "0030_team1_multi_broker_messaging_runtime",
    ]
    assert len(report["registry_checksum"]) == 64


def test_certification_manifest_is_bound_to_real_producers():
    result = validate(ROOT / "docs/release/beta-1-certification-manifest.yaml", ROOT)
    assert result["status"] == "pass", result["errors"]


def test_manifest_validator_rejects_missing_workflow(tmp_path):
    source = (ROOT / "docs/release/beta-1-certification-manifest.yaml").read_text()
    path = tmp_path / "manifest.yaml"
    path.write_text(source.replace("beta-security-hardening.yml", "missing.yml"))
    assert any("does not exist" in item for item in validate(path, ROOT)["errors"])


def test_independent_verifier_fails_closed_and_enforces_no_publish(tmp_path):
    source = json.loads((ROOT / "evidence/beta-1-rc1-release-manifest.json").read_text())
    source["target_sha"] = "a" * 40
    source["publish_status"] = "published"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(source))
    result = verify(path, tmp_path)
    assert result["status"] == "fail"
    assert "publish status must be not_published" in result["errors"]


def test_active_release_gates_do_not_pin_stale_terminal():
    forbidden = "terminal_migration: 0021_lineage_analysis_explorer"
    for base in (ROOT / ".github/workflows", ROOT / "docs/release", ROOT / "scripts/release"):
        for path in base.rglob("*"):
            if path.is_file():
                assert forbidden not in path.read_text(errors="ignore"), path
