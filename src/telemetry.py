"""
DataObs — OpenTelemetry SDK Initialization (Python)
====================================================
Drop-in SDK bootstrap for all DataObs Python services (API, quality engine, sample app).
Implements full OTel semantic conventions v1.26+:
  https://opentelemetry.io/docs/specs/semconv/

Usage:
    from src.telemetry import init_telemetry
    init_telemetry()   # call once at application startup

All resource attributes are read from environment variables so the same code
works in every environment (local, Docker, EC2, ECS, EKS) without changes.
Required env vars (set in docker-compose, Helm, or ECS task definition):
    OTEL_SERVICE_NAME             e.g. dataobs-api
    OTEL_SERVICE_VERSION          e.g. 1.2.3
    OTEL_EXPORTER_OTLP_ENDPOINT   e.g. http://otel-collector:4317
    OTEL_EXPORTER_OTLP_PROTOCOL   grpc (default) or http/protobuf
    OTEL_RESOURCE_ATTRIBUTES      comma-separated key=value pairs for extra attrs

Optional env vars with sensible defaults:
    SERVICE_NAMESPACE             default: dataobs
    DEPLOY_ENV                    default: production
    OTEL_SDK_DISABLED             set to "true" to fully disable SDK (useful in tests)
"""

import os
import socket
import uuid

from opentelemetry import metrics, trace

# ── Logging instrumentation ──────────────────────────────────────────────────
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import OTELResourceDetector, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased


def _build_resource() -> Resource:
    """
    Build a Resource conforming to OTel semconv resource attributes.

    Priority order (highest to lowest):
      1. OTEL_RESOURCE_ATTRIBUTES env var (key=value,key=value)
      2. Explicit well-known OTEL_* env vars
      3. Hardcoded defaults
    """
    # semconv 1.24+: deployment.environment.name is the canonical attribute.
    # We also set the deprecated deployment.environment for backward compat
    # with older Kibana/ES dashboards and Grafana data sources.
    deploy_env = os.getenv("DEPLOY_ENV", os.getenv("DEPLOYMENT_ENVIRONMENT", "production"))
    service_instance_id = os.getenv(
        "POD_NAME", os.getenv("ECS_TASK_ID", f"{os.getenv('OTEL_SERVICE_NAME', 'dataobs')}-{uuid.uuid4().hex[:8]}")
    )

    base_attributes = {
        # ── Required semconv resource attributes ─────────────────────────────
        # https://opentelemetry.io/docs/specs/semconv/resource/#service
        "service.name": os.getenv("OTEL_SERVICE_NAME", "dataobs-unknown"),
        "service.version": os.getenv("OTEL_SERVICE_VERSION", "0.0.0"),
        "service.namespace": os.getenv("SERVICE_NAMESPACE", "dataobs"),
        "service.instance.id": service_instance_id,
        # ── Deployment ────────────────────────────────────────────────────────
        # https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/
        "deployment.environment.name": deploy_env,  # canonical (semconv 1.24+)
        "deployment.environment": deploy_env,  # back-compat alias
        # ── Process / runtime ─────────────────────────────────────────────────
        # https://opentelemetry.io/docs/specs/semconv/resource/process/
        "process.pid": os.getpid(),
        "process.runtime.name": "CPython",
        "process.runtime.version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        # ── Host ─────────────────────────────────────────────────────────────
        # https://opentelemetry.io/docs/specs/semconv/resource/host/
        "host.name": socket.gethostname(),
        # ── Telemetry SDK ─────────────────────────────────────────────────────
        # (automatically set by the SDK — listed here for documentation)
        # "telemetry.sdk.name": "opentelemetry",
        # "telemetry.sdk.language": "python",
        # "telemetry.sdk.version": <SDK version>,
        # ── DataObs custom attributes (dataobs.* namespace) ───────────────────
        "dataobs.product": "dataobs",
        "dataobs.version": os.getenv("DATAOBS_VERSION", "1.0.0"),
    }

    # Merge with attributes from OTEL_RESOURCE_ATTRIBUTES env var (highest priority).
    # OTELResourceDetector reads OTEL_RESOURCE_ATTRIBUTES automatically.
    sdk_detected = OTELResourceDetector().detect()
    return Resource.create(base_attributes).merge(sdk_detected)


def init_telemetry(
    sample_rate: float = 1.0,
    export_timeout_ms: int = 30_000,
) -> None:
    """
    Initialize OTel SDK: traces, metrics, logs.

    Args:
        sample_rate:      Fraction of traces to sample (0.0–1.0). Parent-based: if parent
                          is sampled, child inherits. Defaults to 1.0 (sample everything).
        export_timeout_ms: OTLP export timeout in milliseconds.
    """
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    resource = _build_resource()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # ── Traces ────────────────────────────────────────────────────────────────
    sampler = ParentBased(root=TraceIdRatioBased(sample_rate))
    tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint, timeout=export_timeout_ms // 1000),
            max_queue_size=4096,
            max_export_batch_size=512,
            export_timeout_millis=export_timeout_ms,
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ───────────────────────────────────────────────────────────────
    # Metric names follow semconv: https://opentelemetry.io/docs/specs/semconv/general/metrics/
    # Custom DataObs metrics use the dataobs.* namespace.
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, timeout=export_timeout_ms // 1000),
        export_interval_millis=30_000,
        export_timeout_millis=export_timeout_ms,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ── Logs ──────────────────────────────────────────────────────────────────
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=endpoint, timeout=export_timeout_ms // 1000),
            max_queue_size=2048,
            max_export_batch_size=256,
            export_timeout_millis=export_timeout_ms,
        )
    )
    set_logger_provider(logger_provider)
