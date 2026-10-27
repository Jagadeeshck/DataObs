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


def test_mvp_compose_has_ordered_migrations_and_no_secret_defaults():
    text = (ROOT / "docker-compose.mvp.yml").read_text()
    compose = yaml.safe_load(text)
    assert set(compose["services"]) == {"elasticsearch", "migrations", "demo-seed", "api", "console"}
    api_dependencies = compose["services"]["api"]["depends_on"]
    assert api_dependencies["migrations"]["condition"] == "service_completed_successfully"
    assert api_dependencies["demo-seed"]["condition"] == "service_completed_successfully"
    assert "ELASTIC_PASSWORD:?" in text
    assert "DATAOBS_API_TOKEN:?" in text
    assert compose["services"]["api"]["read_only"] is True
    assert compose["services"]["console"]["read_only"] is True
    assert compose["services"]["demo-seed"]["read_only"] is True


def test_console_container_preserves_api_route_prefix():
    nginx = (ROOT / "ui/dataobs-console/nginx.conf").read_text()
    assert "proxy_pass http://api:8080;" in nginx
    assert "proxy_pass http://api:8080/;" not in nginx


def test_mvp_demo_script_is_bounded_and_verifies_tenant_isolation():
    script = (ROOT / "scripts/demo_mvp.sh").read_text()
    assert "deadline=$((SECONDS + 300))" in script
    assert "http://127.0.0.1:3000/api/v1/auth/me" in script
    assert "command-center?environment=production" in script
    assert 'assert "northstar" not in serialized' in script
    assert "docker compose" in script
    assert "--volumes" not in script


def test_mvp_demo_workflow_is_non_certifying_and_replays_verification():
    workflow = (ROOT / ".github/workflows/first-mvp-demo-smoke.yml").read_text()
    assert "./scripts/demo_mvp.sh up" in workflow
    assert "./scripts/demo_mvp.sh verify" in workflow
    assert '"independent_verification": False' in workflow
    assert '"release_authorization": False' in workflow
    assert "openssl rand -hex 24" in workflow


def test_stable_integration_gate_contract():
    gate_path = ROOT / ".github/workflows/team-delivery-foundation.yml"
    gate = yaml.safe_load(gate_path.read_text())
    triggers = gate.get("on", gate.get(True, {}))
    assert "pull_request" in triggers
    assert gate["jobs"]["foundation-backend"]["uses"].endswith("reusable-backend-validation.yml")
    assert gate["jobs"]["foundation-console"]["uses"].endswith("reusable-console-validation.yml")
    assert "backend" not in gate["jobs"] and "console" not in gate["jobs"]

    backend = (ROOT / ".github/workflows/reusable-backend-validation.yml").read_text()
    for check in (
        "check_team_boundaries.py",
        "check_generated_artifacts.py",
        "check_docs_links.py",
        "validate_capability_ledger.py",
        "validate_migration_graph.py",
        "check_release_metadata.py",
        "check_route_permissions.py",
        "validate_workflow_security.py",
    ):
        assert check in backend

    assert "tenant_isolation_result':'pass' if isolation_path else 'not_run'" in backend
    assert "independent_verification_result':'pending'" in backend

    console = (ROOT / ".github/workflows/reusable-console-validation.yml").read_text()
    assert "browser=${{ inputs.run-playwright && 'pass' || 'not_run' }}" in console
    assert "accessibility=${{ inputs.run-accessibility && inputs.run-playwright && 'pass' || 'not_run' }}" in console


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
