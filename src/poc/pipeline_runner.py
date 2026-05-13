"""
DataObs POC pipeline runner.

The runner is intentionally resilient for demos:
  * exports OTel signals when the SDK/exporters are installed, otherwise logs only
  * writes to Elasticsearch when reachable, otherwise uses an in-memory sink in
    auto mode
  * uses Spark when available, otherwise runs the same transform in Python

Set ``DATAOBS_POC_SINK=elasticsearch`` or ``DATAOBS_POC_SPARK_MODE=spark`` to
make missing infrastructure fail fast in CI or production-like validation.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional, Protocol

logger = logging.getLogger(__name__)

OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318").rstrip("/")
ES_HOST = os.environ.get("ELASTICHOST") or os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "changeme")
ES_USER = os.environ.get("ELASTIC_USERNAME") or os.environ.get("ELASTICSEARCH_USER", "elastic")

_OTEL_REQUIRED_MODULES = (
    "opentelemetry",
    "opentelemetry.exporter.otlp.proto.http._log_exporter",
    "opentelemetry.exporter.otlp.proto.http.metric_exporter",
    "opentelemetry.exporter.otlp.proto.http.trace_exporter",
    "opentelemetry.sdk._logs",
    "opentelemetry.sdk._logs.export",
    "opentelemetry.sdk.metrics",
    "opentelemetry.sdk.metrics.export",
    "opentelemetry.sdk.resources",
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.trace.export",
)
def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


_OTEL_AVAILABLE = all(_module_available(module) for module in _OTEL_REQUIRED_MODULES)

if _OTEL_AVAILABLE:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry._logs import set_logger_provider
else:  # pragma: no cover - exercised by smoke command in minimal envs.
    metrics = trace = None  # type: ignore[assignment]


class MetricLike(Protocol):
    def add(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None: ...
    def record(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None: ...


class NoopMetric:
    def add(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None:
        return None

    def record(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None:
        return None


class NoopSpan:
    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def record_exception(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class NoopTracer:
    @contextmanager
    def start_as_current_span(self, _name: str, attributes: Optional[Dict[str, Any]] = None):
        yield NoopSpan()


class PipelineSink(Protocol):
    def index_test_data(self, docs: Iterable[Dict[str, Any]]) -> int: ...
    def index_spark_results(self, docs: Iterable[Dict[str, Any]]) -> int: ...
    def index_lineage(self, doc: Dict[str, Any]) -> None: ...


@dataclass
class InMemoryPipelineSink:
    """Local fallback sink that lets the PoC run without Elasticsearch."""

    documents: Dict[str, list[Dict[str, Any]]] = field(default_factory=dict)

    def _index_many(self, index: str, docs: Iterable[Dict[str, Any]]) -> int:
        bucket = self.documents.setdefault(index, [])
        count = 0
        for doc in docs:
            bucket.append(dict(doc))
            count += 1
        return count

    def index_test_data(self, docs: Iterable[Dict[str, Any]]) -> int:
        return self._index_many("dataobs-test-data", docs)

    def index_spark_results(self, docs: Iterable[Dict[str, Any]]) -> int:
        return self._index_many("dataobs-spark-results", docs)

    def index_lineage(self, doc: Dict[str, Any]) -> None:
        self._index_many("dataobs-lineage", [doc])


class ElasticsearchPipelineSink:
    """Elasticsearch-backed sink for the Docker Compose POC."""

    def __init__(self, host: str = ES_HOST, user: str = ES_USER, password: str = ES_PASS) -> None:
        from elasticsearch import Elasticsearch

        self.es = Elasticsearch(host, basic_auth=(user, password), verify_certs=False, request_timeout=30)

    def ready(self) -> bool:
        return bool(self.es.ping())

    def _index_many(self, index: str, docs: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for doc in docs:
            self.es.index(index=index, document=doc)
            count += 1
        return count

    def index_test_data(self, docs: Iterable[Dict[str, Any]]) -> int:
        return self._index_many("dataobs-test-data", docs)

    def index_spark_results(self, docs: Iterable[Dict[str, Any]]) -> int:
        return self._index_many("dataobs-spark-results", docs)

    def index_lineage(self, doc: Dict[str, Any]) -> None:
        self.es.index(index="dataobs-lineage", document=doc)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_ok() -> Any:
    return trace.StatusCode.OK if _OTEL_AVAILABLE else None


def _status_error() -> Any:
    return trace.StatusCode.ERROR if _OTEL_AVAILABLE else None


class DataObsPipelineRunner:
    """Orchestrates the runnable DataObs POC pipeline."""

    SERVICE_NAME = "dataobs-pipeline"

    def __init__(self, tenant: str = "poc", run_id: Optional[str] = None, sink: Optional[PipelineSink] = None):
        self.tenant = tenant
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._sink = sink
        self._tracer_provider: Any = None
        self._meter_provider: Any = None
        self._logger_provider: Any = None
        self._tracer: Any = NoopTracer()
        self._rows_counter: MetricLike = NoopMetric()
        self._stage_histogram: MetricLike = NoopMetric()
        self._quality_gauge: MetricLike = NoopMetric()
        self._pipeline_errors: MetricLike = NoopMetric()
        self._pipeline_start = 0.0
        self.last_summary: Dict[str, Any] = {}

    def _bootstrap_otel(self) -> None:
        if not _OTEL_AVAILABLE or os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
            logger.info("[Pipeline] OTel SDK/exporters unavailable or disabled; using logger-only telemetry.")
            return

        resource = Resource.create({
            "service.name": self.SERVICE_NAME,
            "service.namespace": "dataobs",
            "service.instance.id": self.run_id,
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "poc"),
            "pipeline.tenant": self.tenant,
            "telemetry.source": "dataobs-pipeline",
            "monitoring.layer": "data-pipeline",
        })

        self._tracer_provider = TracerProvider(resource=resource)
        self._tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
        trace.set_tracer_provider(self._tracer_provider)
        self._tracer = self._tracer_provider.get_tracer("dataobs.pipeline")

        reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics"), export_interval_millis=15_000)
        self._meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(self._meter_provider)
        meter = self._meter_provider.get_meter("dataobs.pipeline")
        self._rows_counter = meter.create_counter("pipeline.rows.processed", unit="{rows}")
        self._stage_histogram = meter.create_histogram("pipeline.stage.duration_seconds", unit="s")
        self._quality_gauge = meter.create_up_down_counter("pipeline.data.quality_score", unit="{score}")
        self._pipeline_errors = meter.create_counter("pipeline.errors", unit="{errors}")

        self._logger_provider = LoggerProvider(resource=resource)
        self._logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{OTEL_ENDPOINT}/v1/logs")))
        set_logger_provider(self._logger_provider)
        logger.info("[Pipeline] OTel bootstrap complete -> %s", OTEL_ENDPOINT)

    def _shutdown_otel(self) -> None:
        for provider in (self._tracer_provider, self._meter_provider, self._logger_provider):
            if provider:
                try:
                    provider.shutdown()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("[Pipeline] Ignoring telemetry shutdown error: %s", exc)

    def _resolve_sink(self) -> PipelineSink:
        if self._sink:
            return self._sink

        mode = os.environ.get("DATAOBS_POC_SINK", "auto").lower()
        if mode == "memory":
            logger.info("[Pipeline] Using in-memory sink (DATAOBS_POC_SINK=memory).")
            self._sink = InMemoryPipelineSink()
            return self._sink

        try:
            es_sink = ElasticsearchPipelineSink()
            if es_sink.ready():
                logger.info("[Pipeline] Using Elasticsearch sink -> %s", ES_HOST)
                self._sink = es_sink
                return self._sink
            raise ConnectionError(f"Elasticsearch ping failed for {ES_HOST}")
        except Exception as exc:  # noqa: BLE001
            if mode == "elasticsearch":
                raise
            logger.warning("[Pipeline] Elasticsearch unavailable (%s); using in-memory sink.", exc)
            self._sink = InMemoryPipelineSink()
            return self._sink

    def _run_stage(self, name: str, fn: Callable[[], Any], attrs: Optional[Dict[str, Any]] = None) -> Any:
        stage_attrs = attrs or {}
        start = time.time()
        with self._tracer.start_as_current_span(
            f"pipeline/{name}",
            attributes={"pipeline.stage": name, "pipeline.tenant": self.tenant, "pipeline.run_id": self.run_id, **stage_attrs},
        ) as span:
            try:
                result = fn()
                span.set_status(_status_ok())
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(_status_error(), str(exc))
                self._pipeline_errors.add(1, {"pipeline.stage": name})
                logger.error("[Pipeline] Stage '%s' failed: %s", name, exc)
                raise
            finally:
                duration = time.time() - start
                self._stage_histogram.record(duration, {"pipeline.stage": name})
                logger.info("[Pipeline] Stage '%s' completed in %.2fs", name, duration)

    def _stage_ingest(self) -> int:
        docs = [
            {
                "@timestamp": _utc_now(),
                "run_id": self.run_id,
                "record_id": i,
                "value": i * 1.5,
                "source": "poc-pipeline",
                "tenant": self.tenant,
            }
            for i in range(50)
        ]
        rows = self._resolve_sink().index_test_data(docs)
        self._rows_counter.add(rows, {"pipeline.stage": "ingest", "source": type(self._resolve_sink()).__name__})
        logger.info("[Pipeline] Ingested %d test records", rows)
        return rows

    def _stage_spark_transform(self) -> int:
        mode = os.environ.get("DATAOBS_POC_SPARK_MODE", "auto").lower()
        if mode == "mock":
            return self._stage_mock_transform(write_results=True)

        spark = None
        spark_modules_available = _module_available("pyspark") and _module_available("pyspark.sql") and _OTEL_AVAILABLE
        if not spark_modules_available:
            if mode == "spark":
                raise RuntimeError("Spark mode requested, but PySpark or OTel Spark instrumentation dependencies are unavailable")
            logger.warning("[Pipeline] Spark dependencies unavailable; running mock transform.")
            return self._stage_mock_transform(write_results=True)

        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from src.poc.spark_instrumentation import SparkOtelInstrumentation

        try:
            spark = (
                SparkSession.builder.appName(f"DataObs-POC-{self.run_id}")
                .master(os.environ.get("SPARK_MASTER", "local[*]"))
                .config("spark.driver.memory", "512m")
                .config("spark.executor.memory", "512m")
                .config("spark.sql.session.timeZone", "UTC")
                .config("spark.ui.enabled", "false")
                .getOrCreate()
            )

            with SparkOtelInstrumentation(spark, job_name=f"dataobs-transform-{self.run_id}", extra_resource={"pipeline.run_id": self.run_id}) as sotel:
                with sotel.stage("read_input", {"data.source": "inline"}):
                    df = spark.createDataFrame([(i, float(i * 1.5), self.run_id) for i in range(100)], schema=["record_id", "value", "run_id"])

                with sotel.stage("transform", {"transform.type": "filter_aggregate"}):
                    df_transformed = (
                        df.filter(F.col("value") > 10)
                        .withColumn("value_doubled", F.col("value") * 2)
                        .withColumn("processed_at", F.lit(_utc_now()))
                    )

                with sotel.stage("quality_check", {"quality.rule": "null_check"}):
                    null_count = df_transformed.filter(F.col("value").isNull()).count()
                    row_count = df_transformed.count()
                    quality_score = 100.0 if row_count == 0 or null_count == 0 else round((1 - null_count / row_count) * 100, 2)
                    self._quality_gauge.add(int(quality_score), {"dataset": "poc-transform", "pipeline.stage": "quality_check"})

                with sotel.stage("write_output", {"data.sink": type(self._resolve_sink()).__name__}):
                    docs = [
                        {
                            "@timestamp": _utc_now(),
                            "run_id": row.run_id,
                            "record_id": row.record_id,
                            "value": row.value,
                            "value_doubled": row.value_doubled,
                            "processed_at": row.processed_at,
                        }
                        for row in df_transformed.collect()
                    ]
                    self._resolve_sink().index_spark_results(docs)

                sotel.emit_metrics(df_transformed, stage="transform")

            logger.info("[Pipeline] Spark transform stage complete")
            return row_count
        except Exception as exc:  # noqa: BLE001
            if mode == "spark":
                raise
            logger.warning("[Pipeline] Spark unavailable or failed (%s); running mock transform.", exc)
            return self._stage_mock_transform(write_results=True)
        finally:
            if spark is not None:
                spark.stop()

    def _stage_mock_transform(self, write_results: bool = False) -> int:
        docs = [
            {
                "@timestamp": _utc_now(),
                "run_id": self.run_id,
                "record_id": i,
                "value": i * 1.5,
                "value_doubled": i * 3.0,
                "processed_at": _utc_now(),
            }
            for i in range(100)
            if i * 1.5 > 10
        ]
        if write_results:
            self._resolve_sink().index_spark_results(docs)
        self._rows_counter.add(len(docs), {"pipeline.stage": "transform", "source": "mock"})
        self._quality_gauge.add(100, {"dataset": "poc-transform", "pipeline.stage": "quality_check"})
        logger.info("[Pipeline] Mock transform: %d rows", len(docs))
        return len(docs)

    def _stage_lineage(self) -> None:
        lineage_doc = {
            "@timestamp": _utc_now(),
            "run_id": self.run_id,
            "tenant": self.tenant,
            "source_index": "dataobs-test-data",
            "sink_index": "dataobs-spark-results",
            "pipeline": self.SERVICE_NAME,
            "lineage_type": "transformation",
            "row_count": 100,
        }
        self._resolve_sink().index_lineage(lineage_doc)
        logger.info("[Pipeline] Lineage event written")

    def run(self) -> Dict[str, Any]:
        self._bootstrap_otel()
        self._pipeline_start = time.time()
        summary: Dict[str, Any] = {"run_id": self.run_id, "tenant": self.tenant}

        with self._tracer.start_as_current_span(
            "pipeline/run",
            attributes={"pipeline.run_id": self.run_id, "pipeline.tenant": self.tenant, "service.name": self.SERVICE_NAME},
        ) as root_span:
            try:
                summary["ingested_rows"] = self._run_stage("ingest", self._stage_ingest)
                summary["transformed_rows"] = self._run_stage("spark_transform", self._stage_spark_transform)
                self._run_stage("lineage", self._stage_lineage)
                summary["duration_seconds"] = round(time.time() - self._pipeline_start, 3)
                summary["sink"] = type(self._resolve_sink()).__name__
                root_span.set_attribute("pipeline.total_duration_seconds", summary["duration_seconds"])
                root_span.set_status(_status_ok())
                logger.info("[Pipeline] Run %s completed: %s", self.run_id, summary)
                self.last_summary = summary
                return summary
            except Exception as exc:
                root_span.record_exception(exc)
                root_span.set_status(_status_error(), str(exc))
                logger.error("[Pipeline] Run %s FAILED: %s", self.run_id, exc)
                logger.error(traceback.format_exc())
                raise
            finally:
                self._shutdown_otel()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    DataObsPipelineRunner(tenant=os.environ.get("DATAOBS_TENANT_ID", "poc")).run()
