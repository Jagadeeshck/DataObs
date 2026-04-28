"""
Telemetry emitter for the POC pipeline.

Two modes
---------
1. **OTel SDK** (preferred) — if ``opentelemetry-sdk`` and
   ``opentelemetry-exporter-otlp-proto-http`` are installed the emitter
   exports real OTLP traces/metrics to the configured endpoint.
2. **Logger fallback** — when the SDK is not installed every event is
   still emitted as a structured log line so the pipeline always runs
   regardless of whether a full OTel stack is present.

The stage() context manager wraps each pipeline stage with a span/log
bracket and records duration_ms + status as a metric.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False


class TelemetryEmitter:
    """
    Unified telemetry emitter for the DataObs POC pipeline.

    Args:
        service_name:       OTel service.name attribute.
        otlp_endpoint:      OTLP HTTP endpoint, e.g. http://otel-collector:4318.
        use_otel_sdk:       Force-enable (True) or force-disable (False) OTel SDK.
                            Default None = auto-detect.
    """

    def __init__(
        self,
        service_name: str = "dataobs-poc-pipeline",
        otlp_endpoint: Optional[str] = None,
        use_otel_sdk: Optional[bool] = None,
    ) -> None:
        self.service_name = service_name
        self._otel_enabled = False
        self._tracer = None
        self._meter = None
        self._duration_histogram = None
        self._records_counter = None

        sdk_requested = use_otel_sdk if use_otel_sdk is not None else _OTEL_AVAILABLE
        if sdk_requested and _OTEL_AVAILABLE and otlp_endpoint:
            try:
                resource = Resource.create({"service.name": service_name})
                # Traces
                tracer_provider = TracerProvider(resource=resource)
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces"))
                )
                trace.set_tracer_provider(tracer_provider)
                self._tracer = trace.get_tracer(service_name)
                # Metrics
                metric_reader = PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
                )
                meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
                metrics.set_meter_provider(meter_provider)
                self._meter = metrics.get_meter(service_name)
                self._duration_histogram = self._meter.create_histogram(
                    "poc.stage.duration_ms", unit="ms", description="Pipeline stage duration"
                )
                self._records_counter = self._meter.create_counter(
                    "poc.records.ingested", unit="{records}", description="Records ingested per dataset"
                )
                self._otel_enabled = True
                logger.info("[telemetry] OTel SDK initialised — exporting to %s", otlp_endpoint)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[telemetry] OTel SDK init failed, falling back to logger: %s", exc)
        else:
            logger.info("[telemetry] Running in logger-only mode (OTel SDK not configured).")

    # ── Primitives ──────────────────────────────────────────────────────────

    def emit_log(self, stage: str, message: str, **attrs: Any) -> None:
        logger.info("[telemetry][stage=%s] %s | %s", stage, message, attrs)

    def emit_metric(self, name: str, value: float, **attrs: Any) -> None:
        if self._otel_enabled and self._duration_histogram and name == "stage_duration_ms":
            self._duration_histogram.record(value, attributes=attrs)
        elif self._otel_enabled and self._records_counter and name == "records_ingested":
            self._records_counter.add(int(value), attributes=attrs)
        logger.info("[telemetry][metric=%s] value=%s attrs=%s", name, value, attrs)

    def emit_quality_event(self, dataset: str, status: str, **attrs: Any) -> None:
        logger.info("[telemetry][quality] dataset=%s status=%s attrs=%s", dataset, status, attrs)

    def emit_lineage(self, source: str, target: str, relation: str = "transforms_to") -> None:
        logger.info("[telemetry][lineage] %s -(%s)-> %s", source, relation, target)

    # ── Stage context manager ────────────────────────────────────────────────

    @contextmanager
    def stage(self, stage_name: str, **attrs: Any):
        """
        Context manager that wraps a pipeline stage with a span + duration metric.

        Usage::

            with telemetry.stage("transform", dataset="road-safety"):
                df = spark.createDataFrame(records)
        """
        start = time.perf_counter()
        span_ctx = None

        if self._otel_enabled and self._tracer:
            span_ctx = self._tracer.start_as_current_span(stage_name, attributes=attrs)
            span_ctx.__enter__()

        self.emit_log(stage_name, "stage_started", **attrs)
        try:
            yield
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            self.emit_metric("stage_duration_ms", elapsed_ms, stage=stage_name, status="success", **attrs)
            self.emit_log(stage_name, "stage_completed", elapsed_ms=elapsed_ms, status="success", **attrs)
            if span_ctx:
                span_ctx.__exit__(None, None, None)
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            self.emit_metric("stage_duration_ms", elapsed_ms, stage=stage_name, status="failure", **attrs)
            self.emit_log(stage_name, "stage_failed", error=str(exc), elapsed_ms=elapsed_ms, **attrs)
            if span_ctx:
                import sys
                span_ctx.__exit__(*sys.exc_info())
            raise
