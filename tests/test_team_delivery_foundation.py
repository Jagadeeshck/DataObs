import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_team_boundary_contract():
    subprocess.run([sys.executable, "scripts/check_team_boundaries.py"], cwd=ROOT, check=True)


def test_workflow_yaml():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        assert yaml.safe_load(path.read_text())


def test_console_compatibility_and_modules():
    assert 'export * from "./index"' in (ROOT / "ui/dataobs-console/src/api/client.ts").read_text()
    for name in ("streams", "pathways", "jobs", "lineage", "quality", "incidents", "dataProducts", "assets"):
        assert (ROOT / f"ui/dataobs-console/src/api/{name}.ts").exists()


def test_common_evidence_contract():
    text = (ROOT / "ui/dataobs-console/src/api/common.ts").read_text()
    for value in ("complete", "partial", "stale", "not_configured", "unknown", "unavailable"):
        assert f'"{value}"' in text
    assert (ROOT / "ui/dataobs-console/src/api/index.ts").read_text().count("interface EvidenceEnvelope") == 0


def test_templates_and_codeowners():
    pr = (ROOT / ".github/pull_request_template.md").read_text()
    for section in ("Team", "Capability", "Contract impact", "Migration impact", "Hosted evidence", "Rollback"):
        assert f"## {section}" in pr
    assert "@Jagadeeshck" in (ROOT / ".github/CODEOWNERS").read_text()


def test_capability_ownership_metadata_schema():
    data = yaml.safe_load((ROOT / "docs/product/capability-ledger.yaml").read_text())
    assert set(data["ownership_metadata_schema"]["optional_fields"]) == {
        "owner_team",
        "release_target",
        "contract_status",
        "implementation_status",
        "certification_status",
    }
