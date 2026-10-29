import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_console_api_ports_are_one_contract():
    compose = yaml.safe_load((ROOT / "docker-compose.certification.yml").read_text())
    nginx = (ROOT / "ui/dataobs-console/nginx.conf").read_text()
    api = compose["services"]["api"]
    console = compose["services"]["console"]
    assert api["ports"] == ["127.0.0.1:18000:8080"]
    assert console["ports"] == ["127.0.0.1:18080:8080"]
    # No trailing slash: nginx must preserve the /api prefix expected by FastAPI.
    assert re.search(r"proxy_pass\s+http://api:8080;", nginx)
    assert "api:8000" not in nginx


def test_certification_playwright_has_no_vite_web_server():
    config = (ROOT / "ui/dataobs-console/playwright.certification.config.ts").read_text()
    assert "PLAYWRIGHT_BASE_URL" in config
    assert "18080" in config
    assert "webServer" not in config
    assert "vite preview" not in config


def test_scanner_targets_composed_read_only_secret():
    config = yaml.safe_load((ROOT / "certification/config/postgres-scanner.yaml").read_text())
    postgres = config["postgres"]
    assert (postgres["host"], postgres["port"]) == ("postgres", 5432)
    assert (postgres["database"], postgres["username"]) == ("orders", "dataobs_fixture")
    assert postgres["password_ref"] == "file:///run/secrets/postgres_password"


def test_scanner_cli_config_precedes_run_subcommand():
    compose = yaml.safe_load((ROOT / "docker-compose.certification.yml").read_text())
    scanner = compose["services"]["scanner"]
    assert scanner["command"] == ["--config", "/app/certification/config/postgres-scanner.yaml", "run"]

    dockerfile = (ROOT / "Dockerfile.scanner").read_text()
    assert 'CMD ["--config", "config/postgres-scanner.example.yaml", "run"]' in dockerfile


def test_loopback_certification_services_keep_internal_networks_and_host_bridge():
    compose = yaml.safe_load((ROOT / "docker-compose.certification.yml").read_text())
    networks = compose["networks"]
    assert networks["certification-data"]["internal"] is True
    assert networks["certification-control"]["internal"] is True
    assert networks["certification-denied"]["internal"] is True
    assert networks["certification-host"].get("internal") is not True

    expected = {
        "elasticsearch": "127.0.0.1:19200:9200",
        "postgres": "127.0.0.1:15432:5432",
        "kafka-1": "127.0.0.1:19092:29092",
        "schema-registry": "127.0.0.1:18081:8081",
        "kafka-connect": "127.0.0.1:18083:8083",
    }
    for service, port in expected.items():
        definition = compose["services"][service]
        assert port in definition["ports"]
        assert "certification-host" in definition["networks"]

    kafka = compose["services"]["kafka-1"]["environment"]
    assert "EXTERNAL://127.0.0.1:19092" in kafka["KAFKA_ADVERTISED_LISTENERS"]
    assert "EXTERNAL://:29092" in kafka["KAFKA_LISTENERS"]
