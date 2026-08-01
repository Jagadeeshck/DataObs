"""Deterministic cross-team Beta contract gate (hosted execution remains separate)."""

from pathlib import Path

import yaml

from packages.elastic_store.manifest import migrations, registered_mutable_resources
from scripts.release.release_metadata import terminal_migration
from scripts.release.validate_certification_manifest import validate_manifest
from src.api.app import create_app
from src.security.route_policy import PUBLIC_ROUTES, permission_for_route

ROOT = Path(__file__).resolve().parents[2]


def test_application_openapi_routes_are_explicitly_classified() -> None:
    app = create_app()
    schema = app.openapi()
    assert schema["paths"]
    for route in app.routes:
        if not getattr(route, "path", "").startswith("/api/v1"):
            continue
        for method in (getattr(route, "methods", set()) or set()) - {"HEAD", "OPTIONS"}:
            if (method, route.path) not in PUBLIC_ROUTES:
                assert permission_for_route(method, route.path) is not None


def test_manifest_workflows_artifacts_and_release_metadata_are_consistent() -> None:
    manifest_path = ROOT / "docs/release/beta-1-certification-manifest.yaml"
    assert validate_manifest(manifest_path) == []
    manifest = yaml.safe_load(manifest_path.read_text())
    mandatory = [item for item in manifest["capabilities"] if item["mandatory_for_beta"]]
    assert len({item["artifact"] for item in mandatory}) == len(mandatory)
    assert manifest["terminal_migration"] == terminal_migration() == migrations()[-1].migration_id


def test_registered_resources_and_supported_images_are_real() -> None:
    assert "dataobs-provider-checkpoints-v1" in registered_mutable_resources()
    dockerfiles = {
        "Dockerfile.api",
        "ui/dataobs-console/Dockerfile",
        "Dockerfile.quality",
        "Dockerfile.scanner",
        "Dockerfile.monitor-runtime",
        "Dockerfile.pathway-worker",
        "Dockerfile.kafka-observer",
    }
    assert all((ROOT / item).is_file() for item in dockerfiles)
    assert not (ROOT / "Dockerfile.collection-manager").exists()
