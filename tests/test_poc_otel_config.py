"""Static checks for docker-compose.poc.yml + .env.poc.

The default POC telemetry path is now the Elastic APM Python agent
talking to the APM Server hosted by the Fleet-managed elastic-agent
container at ``http://elastic-agent:8200``. The standalone OTel
Collector is retained behind the ``otel`` Compose profile but is NOT
started by the default ``docker compose up`` / ``docker compose run
pipeline`` flow.

These checks guard the regressions that previously broke the POC:

* ``OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`` left in the
  pipeline environment caused
  ``NameResolutionError(host='otel-collector', port=4318)`` retry-spam.
* The pipeline service waiting on ``otel-collector`` made the whole run
  fail when the collector was absent or unhealthy.

Tests run without Docker and without network access.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OTEL_CONFIG = REPO_ROOT / "config" / "otel-collector-poc.yaml"
COMPOSE_FILE = REPO_ROOT / "docker-compose.poc.yml"
ENV_FILE = REPO_ROOT / ".env.poc"
VALIDATOR = REPO_ROOT / "scripts" / "validate_otel_config.py"


@pytest.fixture(scope="module")
def otel_cfg() -> dict:
    return yaml.safe_load(OTEL_CONFIG.read_text())


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


@pytest.fixture(scope="module")
def env_text() -> str:
    return ENV_FILE.read_text()


# ─── OTel Collector config (still validated for the optional profile) ──


def test_docker_stats_api_version_is_string(otel_cfg: dict) -> None:
    api = otel_cfg["receivers"]["docker_stats"]["api_version"]
    assert isinstance(api, str), (
        f"docker_stats.api_version must be a quoted string in YAML, "
        f"got {type(api).__name__} ({api!r})."
    )


def test_otlp_exposes_grpc_4317_and_http_4318(otel_cfg: dict) -> None:
    protos = otel_cfg["receivers"]["otlp"]["protocols"]
    assert protos["grpc"]["endpoint"] == "0.0.0.0:4317"
    assert protos["http"]["endpoint"] == "0.0.0.0:4318"


def test_health_check_extension_bound_publicly(otel_cfg: dict) -> None:
    ep = otel_cfg["extensions"]["health_check"]["endpoint"]
    assert ep == "0.0.0.0:13133"


def test_extensions_referenced_in_service(otel_cfg: dict) -> None:
    declared = set(otel_cfg["extensions"].keys())
    used = set(otel_cfg["service"]["extensions"])
    assert declared <= used


def test_pipeline_components_exist(otel_cfg: dict) -> None:
    receivers = set(otel_cfg["receivers"].keys())
    processors = set(otel_cfg["processors"].keys())
    exporters = set(otel_cfg["exporters"].keys())
    for name, pipe in otel_cfg["service"]["pipelines"].items():
        for r in pipe.get("receivers", []):
            assert r in receivers, f"pipeline {name}: unknown receiver {r}"
        for p in pipe.get("processors", []):
            assert p in processors, f"pipeline {name}: unknown processor {p}"
        for e in pipe.get("exporters", []):
            assert e in exporters, f"pipeline {name}: unknown exporter {e}"


def test_apm_exporter_uses_otlphttp_not_otlp(otel_cfg: dict) -> None:
    exporters = otel_cfg["exporters"]
    assert "otlphttp/apm" in exporters
    assert "otlp/apm" not in exporters
    apm = exporters["otlphttp/apm"]
    assert "protocol" not in apm


def test_pipelines_reference_otlphttp_apm(otel_cfg: dict) -> None:
    for name, pipe in otel_cfg["service"]["pipelines"].items():
        for ref in pipe.get("exporters", []):
            assert ref != "otlp/apm"


def test_validator_script_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(OTEL_CONFIG)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"validate_otel_config.py failed:\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


# ─── Default POC path: Elastic APM, no standalone OTel Collector ──


def test_otel_collector_is_optional_profile_only(compose: dict) -> None:
    """The standalone OTel Collector must NOT start by default.

    It is gated behind the ``otel`` Compose profile so that
    ``docker compose -f docker-compose.poc.yml up`` and
    ``docker compose run pipeline`` skip it entirely.
    """
    svc = compose["services"]["otel-collector"]
    profiles = svc.get("profiles") or []
    assert "otel" in profiles, (
        "otel-collector must be gated behind the `otel` Compose profile. "
        "Without a profile the default POC run starts the collector and "
        "the pipeline flips back to dialling otel-collector:4318."
    )


def test_pipeline_does_not_depend_on_otel_collector(compose: dict) -> None:
    pipeline = compose["services"]["pipeline"]
    deps = pipeline.get("depends_on", {}) or {}
    assert "otel-collector" not in deps, (
        "pipeline must not depend on otel-collector — that service is "
        "now an optional profile and dialling it from the default path "
        "produces NameResolutionError spam."
    )


def test_pipeline_depends_on_elastic_agent(compose: dict) -> None:
    pipeline = compose["services"]["pipeline"]
    deps = pipeline.get("depends_on", {}) or {}
    assert "elastic-agent" in deps, (
        "pipeline depends_on must include elastic-agent so the APM Server "
        "endpoint (http://elastic-agent:8200) is reachable when the run "
        "starts."
    )


def test_pipeline_env_uses_apm_server_url(compose: dict) -> None:
    env = compose["services"]["pipeline"]["environment"]
    apm_url = env.get("ELASTIC_APM_SERVER_URL", "")
    assert apm_url == "http://elastic-agent:8200", (
        f"pipeline.environment.ELASTIC_APM_SERVER_URL should point at the "
        f"Fleet-managed APM Server at http://elastic-agent:8200; got "
        f"{apm_url!r}."
    )
    assert env.get("ELASTIC_APM_SERVICE_NAME"), (
        "ELASTIC_APM_SERVICE_NAME must be set so traces are grouped by "
        "service in Kibana APM."
    )
    assert env.get("ELASTIC_APM_ENVIRONMENT") == "poc"


def test_pipeline_env_disables_otel_sdk(compose: dict) -> None:
    env = compose["services"]["pipeline"]["environment"]
    assert str(env.get("OTEL_SDK_DISABLED", "")).lower() == "true", (
        "OTEL_SDK_DISABLED=true must be set on the pipeline service so "
        "the OTel SDK never tries to dial otel-collector:4318 in the "
        "default POC path."
    )


def test_pipeline_env_has_no_otlp_endpoint(compose: dict) -> None:
    env = compose["services"]["pipeline"]["environment"]
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in env, (
        "OTEL_EXPORTER_OTLP_ENDPOINT must NOT appear in the default "
        "pipeline environment — it caused NameResolutionError spam when "
        "the collector was absent."
    )


def test_pipeline_env_has_no_spark_otel_opts(compose: dict) -> None:
    env = compose["services"]["pipeline"]["environment"]
    spark_opts = env.get("SPARK_SUBMIT_OPTS", "") or ""
    assert "otel-collector" not in spark_opts, (
        "SPARK_SUBMIT_OPTS must not reference otel-collector in the "
        "default POC path."
    )


def test_env_file_does_not_set_otlp_endpoint(env_text: str) -> None:
    """`.env.poc` must not export OTEL_EXPORTER_OTLP_ENDPOINT.

    Stale local .env.poc.local files were the original cause of the
    pipeline silently re-acquiring an otel-collector:4318 endpoint
    even after the compose file was fixed.
    """
    for line in env_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        assert key != "OTEL_EXPORTER_OTLP_ENDPOINT", (
            "`.env.poc` must not set OTEL_EXPORTER_OTLP_ENDPOINT — the "
            "default POC path uses Elastic APM only."
        )


def test_env_file_advertises_apm_url(env_text: str) -> None:
    assert re.search(
        r"(?m)^ELASTIC_APM_SERVER_URL\s*=\s*http://elastic-agent:8200",
        env_text,
    ), (
        "`.env.poc` must export ELASTIC_APM_SERVER_URL=http://elastic-agent:8200 "
        "so the Python pipeline picks up the APM endpoint."
    )


def test_env_file_disables_otel_sdk(env_text: str) -> None:
    assert re.search(r"(?m)^OTEL_SDK_DISABLED\s*=\s*true", env_text), (
        "`.env.poc` must export OTEL_SDK_DISABLED=true so the OTel SDK "
        "never bootstraps in the default POC pipeline."
    )
