import subprocess
from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/team-0-hosted-core-platform-certification-v1.yml"
ADAPTER = ROOT / "scripts/hosted_certification/certification_phase.sh"


def test_workflow_is_manual_least_privilege_and_never_publishes() -> None:
    raw = WORKFLOW.read_text()
    workflow = yaml.safe_load(raw)
    # PyYAML 1.1 parses the key `on` as True.
    dispatch = workflow.get("on", workflow.get(True))["workflow_dispatch"]
    assert set(dispatch["inputs"]) == {
        "target_sha",
        "certification_profile",
        "capacity_profile",
        "infrastructure_profile",
        "upgrade_source_version",
        "maximum_duration",
        "cleanup_confirmation",
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["certify"]["environment"] == "team-0-hosted-certification-test"
    assert "contents: write" not in raw
    assert "packages: write" not in raw
    assert "release create" not in raw
    assert "if: always()" in raw
    assert "cleanup-report" in raw


def test_adapter_fails_closed_without_protected_driver() -> None:
    result = subprocess.run(
        ["bash", str(ADAPTER), "provision"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={},
    )
    assert result.returncode == 3
    assert "PENDING" in result.stderr


def test_adapter_rejects_unknown_phase() -> None:
    result = subprocess.run(
        ["bash", str(ADAPTER), "publish"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unknown hosted certification phase" in result.stderr
