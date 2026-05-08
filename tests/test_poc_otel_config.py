"""
tests/test_poc_otel_config.py
─────────────────────────────
Guards the default-path OTel configuration rules for the DataObs POC.

These tests exist to prevent regressions where:
  - OTel bootstrap log appeared on default `docker compose run --rm pipeline`
  - Spark downloaded io.opentelemetry JARs on every run
  - TelemetryEmitter attempted to dial otel-collector:4318 even when OTEL_SDK_DISABLED=true

All tests are designed to run without a running Docker environment,
without an OTel collector, and without PySpark installed.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = REPO_ROOT / "config" / "dataobs_poc.yaml"


# ─── Config YAML guards ────────────────────────────────────────────────────


def test_dataobs_poc_yaml_is_valid_yaml() -> None:
    """config/dataobs_poc.yaml must parse without error."""
    cfg = yaml.safe_load(CFG_PATH.read_text())
    assert isinstance(cfg, dict)


def test_spark_config_otel_instrumentation_disabled_by_default() -> None:
    """dataobs_poc.yaml must not enable Spark OTel instrumentation by default.

    When spark.otel_instrumentation_enabled is true, Spark resolves and
    downloads the OTel Java agent (io.opentelemetry:opentelemetry-api) via
    ivy on every container start, adding ~30 s of startup latency and
    requiring network access to Maven Central.
    """
    cfg = yaml.safe_load(CFG_PATH.read_text())
    spark_cfg = cfg.get("spark", {})
    assert not spark_cfg.get("otel_instrumentation_enabled", False), (
        "spark.otel_instrumentation_enabled must be false in the default POC config. "
        "Enable only when running with `docker compose --profile otel`."
    )
    assert not spark_cfg.get("java_agent_enabled", False), (
        "spark.java_agent_enabled must be false in the default POC config. "
        "The Java OTel agent requires the otel-collector service. "
        "Enable only when running with `docker compose --profile otel`."
    )


def test_otel_config_endpoint_empty_by_default() -> None:
    """dataobs_poc.yaml otel.endpoint must be an empty string by default.

    TelemetryEmitter reads otel.endpoint at construction time before the
    OTEL_SDK_DISABLED guard fires. A non-empty value (especially one
    referencing otel-collector:4318) causes the OTel bootstrap log to
    appear in the default docker compose run --rm pipeline output.
    """
    cfg = yaml.safe_load(CFG_PATH.read_text())
    endpoint = cfg.get("otel", {}).get("endpoint", "")
    # The YAML value must not hard-code the otel-collector hostname.
    # (env-var substitution happens at runtime, not in the raw YAML value.)
    assert "otel-collector" not in str(endpoint), (
        "otel.endpoint in dataobs_poc.yaml must not reference otel-collector:4318. "
        "This causes TelemetryEmitter to attempt an OTel bootstrap in the default path. "
        f"Current value: {endpoint!r}"
    )


# ─── TelemetryEmitter unit guards ─────────────────────────────────────────


def test_telemetry_emitter_disabled_when_otel_sdk_disabled(monkeypatch) -> None:
    """TelemetryEmitter must not enable OTel when OTEL_SDK_DISABLED=true.

    Even when an explicit otlp_endpoint is passed the emitter must remain
    in logger-only mode, because OTEL_SDK_DISABLED=true is the canonical
    signal that the collector is not running.
    """
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    # Force module reload so the module-level _OTEL_DISABLED is re-evaluated
    # with the patched environment.
    if "src.poc.telemetry" in sys.modules:
        del sys.modules["src.poc.telemetry"]

    from src.poc.telemetry import TelemetryEmitter

    emitter = TelemetryEmitter(
        service_name="test",
        otlp_endpoint="http://otel-collector:4318",  # explicitly passed but must be ignored
    )
    assert not emitter._otel_enabled, (
        "TelemetryEmitter._otel_enabled must be False when OTEL_SDK_DISABLED=true, "
        "even when an explicit otlp_endpoint is passed."
    )


def test_telemetry_emitter_logger_only_when_no_endpoint(monkeypatch) -> None:
    """TelemetryEmitter must stay in logger-only mode when endpoint is empty."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")  # SDK not disabled
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    if "src.poc.telemetry" in sys.modules:
        del sys.modules["src.poc.telemetry"]

    from src.poc.telemetry import TelemetryEmitter

    emitter = TelemetryEmitter(
        service_name="test",
        otlp_endpoint=None,  # no endpoint
    )
    # Without an endpoint the SDK cannot be configured; must fall through to logger.
    assert not emitter._otel_enabled


def test_no_otel_bootstrap_log_message_in_default_mode(monkeypatch, caplog) -> None:
    """Default mode must not emit the OTel bootstrap complete log line.

    Regression guard: previously the log line
      [Pipeline] OTel bootstrap complete -> http://otel-collector:4318
    appeared on every run because otel.endpoint resolved to a non-empty
    value from the YAML env fallback before the OTEL_SDK_DISABLED guard.
    """
    import logging

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    if "src.poc.telemetry" in sys.modules:
        del sys.modules["src.poc.telemetry"]

    with caplog.at_level(logging.DEBUG, logger="src.poc.telemetry"):
        from src.poc.telemetry import TelemetryEmitter
        TelemetryEmitter(service_name="test", otlp_endpoint=None)

    combined = " ".join(caplog.messages).lower()
    assert "otel bootstrap complete" not in combined
    assert "otel-collector:4318" not in combined
