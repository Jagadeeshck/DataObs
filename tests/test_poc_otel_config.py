"""Static checks for config/otel-collector-poc.yaml + docker-compose.poc.yml.

These regressions previously caused the POC collector container to exit
with code 1 on `docker compose -f docker-compose.poc.yml run --rm pipeline`:

  * docker_stats.api_version parsed as a YAML float (`1.41`) instead of a
    string, which the receiver rejects at config-load time.
  * The POC compose used `service_healthy` to wait on a `FROM scratch`
    collector image whose CMD-SHELL healthcheck was unrunnable.

The tests run without Docker and without network access.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OTEL_CONFIG = REPO_ROOT / "config" / "otel-collector-poc.yaml"
COMPOSE_FILE = REPO_ROOT / "docker-compose.poc.yml"
VALIDATOR = REPO_ROOT / "scripts" / "validate_otel_config.py"


@pytest.fixture(scope="module")
def otel_cfg() -> dict:
    return yaml.safe_load(OTEL_CONFIG.read_text())


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


def test_docker_stats_api_version_is_string(otel_cfg: dict) -> None:
    """A YAML float blows up the collector with `cannot unmarshal !!float`."""
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
    assert ep == "0.0.0.0:13133", (
        "Compose maps host port 13133 → container 13133; "
        "binding to 127.0.0.1 would make the probe unreachable."
    )


def test_extensions_referenced_in_service(otel_cfg: dict) -> None:
    declared = set(otel_cfg["extensions"].keys())
    used = set(otel_cfg["service"]["extensions"])
    assert declared <= used, (
        f"Extensions declared but not enabled in service.extensions: "
        f"{sorted(declared - used)}"
    )


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


def test_collector_image_is_recent_contrib(compose: dict) -> None:
    """0.99.0 is from April 2024 and pre-dates several receiver fixes."""
    image = compose["services"]["otel-collector"]["image"]
    assert image.startswith("otel/opentelemetry-collector-contrib:")
    tag = image.split(":")[1]
    major, minor, *_ = tag.split(".")
    assert int(major) > 0 or int(minor) >= 111, (
        f"otel-collector image {image!r} is older than 0.111.0; "
        "earlier versions have known config-schema bugs that broke "
        "the POC."
    )


def test_collector_has_no_unrunnable_healthcheck(compose: dict) -> None:
    """The contrib image is FROM scratch — no shell, curl, or wget.

    A CMD-SHELL or curl/wget healthcheck always reports unhealthy and
    blocks any downstream `service_healthy` dependency.
    """
    svc = compose["services"]["otel-collector"]
    hc = svc.get("healthcheck")
    if hc is None:
        return  # Preferred: no healthcheck on a distroless image.
    test = hc.get("test", [])
    if isinstance(test, list) and test:
        joined = " ".join(test)
        for forbidden in ("CMD-SHELL", "wget", "curl", "/bin/sh"):
            assert forbidden not in joined, (
                f"otel-collector healthcheck uses {forbidden!r} but the "
                "image is FROM scratch and lacks a shell/curl/wget."
            )


def test_pipeline_does_not_wait_on_otel_service_healthy(compose: dict) -> None:
    """Without a runnable healthcheck, `service_healthy` will hang forever."""
    pipeline = compose["services"]["pipeline"]
    dep = pipeline["depends_on"]["otel-collector"]
    cond = dep if isinstance(dep, str) else dep.get("condition", "")
    assert cond != "service_healthy", (
        "pipeline.depends_on.otel-collector must not be `service_healthy`; "
        "the collector image is FROM scratch and has no Compose-level "
        "healthcheck. Use `service_started` instead."
    )


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


def test_validator_script_catches_float_api_version(tmp_path: Path) -> None:
    bad = yaml.safe_load(OTEL_CONFIG.read_text())
    bad["receivers"]["docker_stats"]["api_version"] = 1.41  # float regression
    bad_path = tmp_path / "bad-otel.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "api_version" in proc.stdout


def test_apm_exporter_uses_otlphttp_not_otlp(otel_cfg: dict) -> None:
    """APM Server speaks OTLP/HTTP on :8200; the gRPC `otlp` exporter has
    no `protocol` key and aborts the collector at config-load time.
    """
    exporters = otel_cfg["exporters"]
    assert "otlphttp/apm" in exporters, (
        "APM exporter must be `otlphttp/apm` (HTTP). The contrib "
        "collector's `otlp` exporter is gRPC-only and rejects the "
        "`protocol` key, which previously crashed the POC at startup."
    )
    assert "otlp/apm" not in exporters, (
        "Rename `otlp/apm` → `otlphttp/apm`; the OTLP gRPC exporter "
        "rejects the `protocol` field and the POC sends to APM Server "
        "on :8200 over HTTP."
    )
    apm = exporters["otlphttp/apm"]
    # Bare otlphttp config — `protocol` is not a valid key on either
    # otlp or otlphttp; if someone re-introduces it the validator
    # below catches it and so does the collector.
    assert "protocol" not in apm


def test_pipelines_reference_otlphttp_apm(otel_cfg: dict) -> None:
    for name, pipe in otel_cfg["service"]["pipelines"].items():
        for ref in pipe.get("exporters", []):
            assert ref != "otlp/apm", (
                f"pipeline {name}: stale `otlp/apm` reference; the "
                f"exporter is now `otlphttp/apm`."
            )


def test_validator_script_catches_otlp_with_protocol_key(tmp_path: Path) -> None:
    """Regression: `otlp/apm: { protocol: http/protobuf, ... }` is the
    exact misconfiguration that produced
        'has invalid keys: protocol' under 'otlp/apm'
    on container start. The static linter must reject it before we
    ever launch the collector.
    """
    bad = yaml.safe_load(OTEL_CONFIG.read_text())
    # Re-introduce the broken shape under the gRPC component id.
    bad["exporters"].pop("otlphttp/apm", None)
    bad["exporters"]["otlp/apm"] = {
        "endpoint": "http://elastic-agent:8200",
        "protocol": "http/protobuf",
        "tls": {"insecure": True},
    }
    # Keep pipelines consistent so we trip *only* the otlp/protocol check.
    for pipe in bad["service"]["pipelines"].values():
        pipe["exporters"] = [
            "otlp/apm" if e == "otlphttp/apm" else e
            for e in pipe.get("exporters", [])
        ]
    bad_path = tmp_path / "bad-otel.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "protocol" in proc.stdout
    assert "otlp/apm" in proc.stdout
