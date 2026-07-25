import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_required_profiles_and_exact_images():
    text = (ROOT / "docker-compose.certification.yml").read_text()
    for profile in ("core", "postgres", "kafka", "jobs", "browser", "security", "full"):
        assert profile in text
    assert ":latest" not in text
    assert "elasticsearch:9.4.2" in text and "kibana:9.4.2" in text


def test_tenant_fixture_overlaps_names():
    fixture = json.loads((ROOT / "certification/fixtures/tenants/manifest.json").read_text())
    assert [x["id"] for x in fixture["tenants"]] == ["tenant-alpha", "tenant-beta"]
    assert fixture["overlapping_resources"]["database"] == "orders"
