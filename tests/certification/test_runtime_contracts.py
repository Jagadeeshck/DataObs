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
    assert re.search(r"proxy_pass\s+http://api:8080/;", nginx)
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
