"""
DataObs Quality Engine — Scheduler Entry Point

Loads quality rules from config/dataobs.yaml (or the path in the
DATAOBS_CONFIG env var) and schedules each dataset's checks using
APScheduler.  Results are indexed to Elasticsearch and emitted as
OpenTelemetry metrics/traces.

Environment variables
---------------------
DATAOBS_CONFIG          Path to the YAML config file (default: config/dataobs.yaml)
ELASTICSEARCH_URL       ES endpoint, e.g. http://elasticsearch:9200
ELASTICSEARCH_USER      ES username (default: elastic)
ELASTICSEARCH_PASSWORD  ES password
OTEL_EXPORTER_OTLP_ENDPOINT  OTLP gRPC endpoint (default: http://localhost:4317)
OTEL_SERVICE_NAME       OTel service name (default: dataobs-quality)
LOG_LEVEL               Python log level (default: INFO)
"""
from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from elasticsearch import Elasticsearch
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.quality.checks.null_check import NullCheck
from src.quality.checks.referential_integrity_check import ReferentialIntegrityCheck
from src.quality.checks.row_count_check import RowCountCheck
from src.quality.checks.schema_check import SchemaCheck
from src.quality.checks.uniqueness_check import UniquenessCheck
from src.quality.checks.value_range_check import ValueRangeCheck
from src.quality.freshness import FreshnessMonitor

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("dataobs.engine")

# ---------------------------------------------------------------------------
# Check registry — maps config type strings to check classes
# ---------------------------------------------------------------------------
CHECK_REGISTRY = {
    "row_count": RowCountCheck,
    "null_check": NullCheck,
    "uniqueness": UniquenessCheck,
    "value_range": ValueRangeCheck,
    "referential_integrity": ReferentialIntegrityCheck,
    "schema_change": SchemaCheck,
}

# ---------------------------------------------------------------------------
# OTel bootstrap
# ---------------------------------------------------------------------------

def _setup_otel(service_name: str, otlp_endpoint: str) -> None:
    """Initialise SDK-level TracerProvider and MeterProvider."""
    resource = Resource.create({"service.name": service_name})

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
        export_interval_millis=60_000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    logger.info("OTel initialised — endpoint: %s  service: %s", otlp_endpoint, service_name)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("Config file not found at %s — using empty config", path)
        return {}
    with config_path.open() as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Elasticsearch client factory
# ---------------------------------------------------------------------------

def _make_es_client(cfg: Dict[str, Any]) -> Elasticsearch:
    es_cfg = cfg.get("elasticsearch", {})
    url = os.getenv("ELASTICSEARCH_URL") or es_cfg.get("url", "http://localhost:9200")
    user = os.getenv("ELASTICSEARCH_USER") or es_cfg.get("username", "elastic")
    password = os.getenv("ELASTICSEARCH_PASSWORD") or es_cfg.get("password", "")
    verify_certs = es_cfg.get("verify_certs", True)

    client = Elasticsearch(
        [url],
        basic_auth=(user, password),
        verify_certs=verify_certs,
        request_timeout=30,
    )
    logger.info("Elasticsearch client initialised — %s", url)
    return client


# ---------------------------------------------------------------------------
# Job runner — called by APScheduler for each dataset rule set
# ---------------------------------------------------------------------------

def _run_checks_for_dataset(
    dataset: str,
    checks_config: List[Dict[str, Any]],
    es_client: Elasticsearch,
) -> None:
    """Execute all configured checks for one dataset and index results to ES."""
    tracer = trace.get_tracer("dataobs.engine")
    meter = metrics.get_meter("dataobs.engine")
    check_counter = meter.create_counter(
        "dataobs.quality.checks_run",
        description="Total quality checks executed",
    )
    failure_counter = meter.create_counter(
        "dataobs.quality.checks_failed",
        description="Total quality checks that returned FAIL status",
    )

    with tracer.start_as_current_span(f"quality_run.{dataset}") as span:
        span.set_attribute("dataobs.dataset", dataset)
        span.set_attribute("dataobs.check_count", len(checks_config))
        logger.info("Running %d checks for dataset: %s", len(checks_config), dataset)

        for check_cfg in checks_config:
            check_type = check_cfg.get("type")
            check_cls = CHECK_REGISTRY.get(check_type)

            if check_cls is None:
                logger.warning("Unknown check type '%s' for dataset %s — skipping", check_type, dataset)
                continue

            try:
                # RowCountCheck optionally accepts an ES client for anomaly detection
                if check_type == "row_count":
                    check = check_cls(es_client=es_client)
                else:
                    check = check_cls()

                # Freshness checks are handled by FreshnessMonitor separately
                result = check.run({"dataset": dataset, **check_cfg}, None)

                check_counter.add(1, {"dataset": dataset, "check_type": check_type})
                if result.status == "FAIL":
                    failure_counter.add(1, {"dataset": dataset, "check_type": check_type, "severity": result.severity})
                    logger.warning(
                        "FAIL — dataset: %s  check: %s  severity: %s  details: %s",
                        dataset, check_type, result.severity, result.details,
                    )

                # Index result to Elasticsearch
                es_client.index(
                    index="dataobs-quality-results",
                    document=result.to_es_doc(),
                )

            except Exception:
                logger.exception("Error running check '%s' for dataset '%s'", check_type, dataset)


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

def _register_jobs(
    scheduler: BlockingScheduler,
    cfg: Dict[str, Any],
    es_client: Elasticsearch,
) -> int:
    """Register one APScheduler job per quality_rules entry. Returns job count."""
    rules: List[Dict[str, Any]] = cfg.get("quality_rules", [])
    job_count = 0

    for rule in rules:
        dataset = rule.get("dataset")
        schedule = rule.get("schedule", "*/15 * * * *")
        checks = rule.get("checks", [])

        if not dataset or not checks:
            logger.warning("Skipping rule with missing dataset or checks: %s", rule)
            continue

        scheduler.add_job(
            _run_checks_for_dataset,
            CronTrigger.from_crontab(schedule),
            args=[dataset, checks, es_client],
            id=f"quality_{dataset}",
            name=f"Quality checks — {dataset}",
            replace_existing=True,
            misfire_grace_time=300,  # allow up to 5 min late start
        )
        logger.info("Registered job for dataset '%s' on schedule '%s'", dataset, schedule)
        job_count += 1

    return job_count


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def _install_signal_handlers(scheduler: BlockingScheduler) -> None:
    def _shutdown(signum, frame):
        logger.info("Received signal %s — shutting down scheduler …", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_path = os.getenv("DATAOBS_CONFIG", "config/dataobs.yaml")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "dataobs-quality")

    logger.info("DataObs Quality Engine starting …")
    logger.info("Config: %s", config_path)

    cfg = _load_config(config_path)
    _setup_otel(service_name, otlp_endpoint)
    es_client = _make_es_client(cfg)

    scheduler = BlockingScheduler(timezone="UTC")
    _install_signal_handlers(scheduler)

    job_count = _register_jobs(scheduler, cfg, es_client)
    logger.info("Registered %d quality check job(s) — starting scheduler", job_count)

    if job_count == 0:
        logger.warning(
            "No quality_rules found in config — engine is running but idle. "
            "Add rules to %s to start monitoring datasets.",
            config_path,
        )

    scheduler.start()


if __name__ == "__main__":
    main()
