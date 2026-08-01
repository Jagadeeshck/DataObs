from __future__ import annotations

from pathlib import Path

import yaml

from scripts.release.release_metadata import terminal_migration
from scripts.release.validate_certification_manifest import validate_manifest


def _fixture(tmp_path: Path) -> Path:
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    (workflows / "proof.yml").write_text(
        "on:\n  workflow_dispatch:\njobs:\n  proof:\n    steps:\n      - uses: actions/upload-artifact@v4\n        with: {name: proof-evidence}\n"
    )
    manifest = {
        "repository": "Jagadeeshck/DataObs",
        "target_elasticsearch_version": "9.4.2",
        "terminal_migration": terminal_migration(),
        "capabilities": [
            {
                "capability_id": "team6.proof",
                "owning_team": "Team 6",
                "workflow": "proof.yml",
                "artifact": "proof-evidence",
                "mandatory_for_beta": True,
                "evidence_schema_version": "1.0",
                "expected_elasticsearch_version": "9.4.2",
                "accepted_events": ["workflow_dispatch"],
                "required_test_categories": ["unit"],
            }
        ],
    }
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(manifest))
    return path


def test_accepts_real_exact_commit_workflow_and_artifact(tmp_path: Path) -> None:
    assert validate_manifest(_fixture(tmp_path), tmp_path) == []


def test_rejects_missing_artifact_optional_reason_and_stale_terminal(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    value = yaml.safe_load(path.read_text())
    entry = value["capabilities"][0]
    value["terminal_migration"] = "0001_stale"
    entry["artifact"] = "not-uploaded"
    entry["mandatory_for_beta"] = False
    path.write_text(yaml.safe_dump(value))
    errors = validate_manifest(path, tmp_path)
    assert any("terminal migration" in item for item in errors)
    assert any("artifact name" in item for item in errors)
    assert any("optional capability" in item for item in errors)
