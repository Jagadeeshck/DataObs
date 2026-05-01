"""
src/poc/pipeline_runner.py
──────────────────────────
Full Data Pipeline runner with complete OTel instrumentation:
  - Root span for entire pipeline run
  - Child spans per stage (ingest, transform, quality, write, lineage)
  - Spark job instrumentation via SparkOtelInstrumentation
  - Structured logs shipped to OTel Collector
  - Metrics: rows processed, stage durations, data quality scores

This is the entry-point that replaces the bare pipeline script and
guarantees everything is visible in Kibana APM + Metrics Explorer.
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

logger = logging.getLogger(__name__)

OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
ES_HOST = os.environ.get("ELASTICHOST", "http://elasticsearch:9200")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "changeme")


class DataObsPipelineRunner:
    """
    Orchestrates the DataObs POC pipeline with full OTel instrumentation.
    Every stage emits traces, metrics and logs to the OTel Collector,
    which routes them to Elasticsearch / Kibana APM.
    """

    SERVICE_NAME = "dataobs-pipeline"

    def __init__(self, tenant: str = "poc", run_id: Optional[str] = None):
        self.tenant = tenant
        self.run_id = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._logger_provider: Optional[LoggerProvider] = None
        self._tracer = None
        self._meter = None
        self._pipeline_start: float = 0.0

    # ── Bootstrap OTel ─────────────────────────────────────────────────────
    def _bootstrap_otel(self):
        resource = Resource.create({
            "service.name": self.SERVICE_NAME,
            "service.namespace": "dataobs",
            "service.instance.id": self.run_id,
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "poc"),
            "pipeline.tenant": self.tenant,
            "telemetry.source": "dataobs-pipeline",
            "monitoring.layer": "data-pipeline",
        })

        # Traces
        span_exporter = OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")
        self._tracer_provider = TracerProvider(resource=resource)
        self._tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(self._tracer_provider)
        self._tracer = self._tracer_provider.get_tracer("dataobs.pipeline")

        # Metrics
        metric_exporter = OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics")
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15_000)
        self._meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(self._meter_provider)
        self._meter = self._meter_provider.get_meter("dataobs.pipeline")

        # Logs
        log_exporter = OTLPLogExporter(endpoint=f"{OTEL_ENDPOINT}/v1/logs")
        self._logger_provider = LoggerProvider(resource=resource)
        self._logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(self._logger_provider)

        # Instruments
        self._rows_counter = self._meter.create_counter(
            "pipeline.rows.processed", unit="{rows}",
            description="Total rows processed by pipeline stage"
        )
        self._stage_histogram = self._meter.create_histogram(
            "pipeline.stage.duration_seconds", unit="s",
            description="Duration of each pipeline stage"
        )
        self._quality_gauge = self._meter.create_up_down_counter(
            "pipeline.data.quality_score", unit="{score}",
            description="Data quality score 0-100 per dataset"
        )
        self._pipeline_errors = self._meter.create_counter(
            "pipeline.errors", unit="{errors}",
            description="Pipeline stage errors"
        )
        logger.info("[Pipeline] OTel bootstrap complete → %s", OTEL_ENDPOINT)

    def _shutdown_otel(self):
        for p in [self._tracer_provider, self._meter_provider, self._logger_provider]:
            try:
                if p:
                    p.shutdown()
            except Exception:
                pass

    # ── Stage runner ───────────────────────────────────────────────────────
    def _run_stage(
        self,
        name: str,
        fn,
        attrs: Dict[str, Any] = {},
    ):
        """
        Execute fn() inside an OTel span. Records duration metric,
        marks span ERROR on exception and re-raises.
        """
        t0 = time.time()
        with self._tracer.start_as_current_span(
            f"pipeline/{name}",
            attributes={
                "pipeline.stage": name,
                "pipeline.tenant": self.tenant,
                "pipeline.run_id": self.run_id,
                **attrs,
            },
        ) as span:
            try:
                result = fn()
                span.set_status(trace.StatusCode.OK)
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                self._pipeline_errors.add(1, {"pipeline.stage": name})
                logger.error("[Pipeline] Stage '%s' failed: %s", name, exc)
                raise
            finally:
                duration = time.time() - t0
                self._stage_histogram.record(duration, {"pipeline.stage": name})
                logger.info("[Pipeline] Stage '%s' completed in %.2fs", name, duration)

    # ── Pipeline stages ────────────────────────────────────────────────────
    def _stage_ingest(self):
        """Simulate data ingestion — reads from ES test-data index."""
        from elasticsearch import Elasticsearch
        es = Elasticsearch(ES_HOST, basic_auth=("elastic", ES_PASS), verify_certs=False)
        # Ingest some synthetic test records into the unified data index
        rows = 0
        for i in range(50):
            es.index(
                index="dataobs-test-data",
                document={
                    "@timestamp": datetime.utcnow().isoformat(),
                    "run_id": self.run_id,
                    "record_id": i,
                    "value": i * 1.5,
                    "source": "poc-pipeline",
                    "tenant": self.tenant,
                },
            )
            rows += 1
        self._rows_counter.add(rows, {"pipeline.stage": "ingest", "source": "elasticsearch"})
        logger.info("[Pipeline] Ingested %d test records", rows)
        return rows

    def _stage_spark_transform(self):
        """Spark transformation stage with full OTel instrumentation."""
        try:
            from pyspark.sql import SparkSession
            from src.poc.spark_instrumentation import SparkOtelInstrumentation

            spark = (
                SparkSession.builder
                .appName(f"DataObs-POC-{self.run_id}")
                .master(os.environ.get("SPARK_MASTER", "local[*]"))
                .config("spark.driver.memory", "512m")
                .config("spark.executor.memory", "512m")
                .config(
                    "spark.jars.packages",
                    "org.apache.spark:spark-sql_2.12:3.4.3,"
                    "io.opentelemetry:opentelemetry-api:1.38.0"
                )
                .getOrCreate()
            )

            with SparkOtelInstrumentation(
                spark,
                job_name=f"dataobs-transform-{self.run_id}",
                extra_resource={"pipeline.run_id": self.run_id},
            ) as sotel:
                # Stage 1: Read synthetic data
                with sotel.stage("read_input", {"data.source": "inline"}):
                    data = [(i, float(i * 1.5), self.run_id) for i in range(100)]
                    schema = ["record_id", "value", "run_id"]
                    df = spark.createDataFrame(data, schema=schema)

                # Stage 2: Transform
                with sotel.stage("transform", {"transform.type": "filter_aggregate"}):
                    from pyspark.sql import functions as F
                    df_transformed = (
                        df.filter(F.col("value") > 10)
                        .withColumn("value_doubled", F.col("value") * 2)
                        .withColumn("processed_at", F.lit(datetime.utcnow().isoformat()))
                    )

                # Stage 3: Quality check
                with sotel.stage("quality_check", {"quality.rule": "null_check"}):
                    null_count = df_transformed.filter(F.col("value").isNull()).count()
                    row_count = df_transformed.count()
                    quality_score = 100.0 if null_count == 0 else round(
                        (1 - null_count / row_count) * 100, 2
                    )
                    self._quality_gauge.add(
                        int(quality_score),
                        {"dataset": "poc-transform", "pipeline.stage": "quality_check"}
                    )
                    logger.info(
                        "[Pipeline] Quality check: %d rows, %d nulls, score=%.1f",
                        row_count, null_count, quality_score
                    )

                # Stage 4: Write results back to ES test-data index
                with sotel.stage("write_output", {"data.sink": "elasticsearch"}):
                    df_results = df_transformed.collect()
                    es_client = __import__("elasticsearch").Elasticsearch(
                        ES_HOST, basic_auth=("elastic", ES_PASS), verify_certs=False
                    )
                    for row in df_results:
                        es_client.index(
                            index="dataobs-spark-results",
                            document={
                                "@timestamp": datetime.utcnow().isoformat(),
                                "run_id": row.run_id,
                                "record_id": row.record_id,
                                "value": row.value,
                                "value_doubled": row.value_doubled,
                                "processed_at": row.processed_at,
                            },
                        )

                sotel.emit_metrics(df_transformed, stage="transform")

            spark.stop()
            logger.info("[Pipeline] Spark transform stage complete")
            return row_count

        except ImportError as exc:
            logger.warning(
                "[Pipeline] PySpark not available (%s) — running mock transform", exc
            )
            return self._stage_mock_transform()

    def _stage_mock_transform(self) -> int:
        """Fallback mock transform when PySpark is unavailable."""
        import math
        rows = 100
        mock_results = [
            {"record_id": i, "value": i * 1.5, "value_doubled": i * 3.0}
            for i in range(rows)
            if i * 1.5 > 10
        ]
        self._rows_counter.add(len(mock_results), {"pipeline.stage": "transform", "source": "mock"})
        logger.info("[Pipeline] Mock transform: %d rows", len(mock_results))
        return len(mock_results)

    def _stage_lineage(self):
        """Emit data lineage event as an OTel span + ES document."""
        from elasticsearch import Elasticsearch
        es = Elasticsearch(ES_HOST, basic_auth=("elastic", ES_PASS), verify_certs=False)
        lineage_doc = {
            "@timestamp": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "tenant": self.tenant,
            "source_index": "dataobs-test-data",
            "sink_index": "dataobs-spark-results",
            "pipeline": self.SERVICE_NAME,
            "lineage_type": "transformation",
            "row_count": 100,
        }
        es.index(index="dataobs-lineage", document=lineage_doc)
        logger.info("[Pipeline] Lineage event written to dataobs-lineage")

    # ── Main run ───────────────────────────────────────────────────────────
    def run(self):
        self._bootstrap_otel()
        self._pipeline_start = time.time()

        with self._tracer.start_as_current_span(
            "pipeline/run",
            attributes={
                "pipeline.run_id": self.run_id,
                "pipeline.tenant": self.tenant,
                "service.name": self.SERVICE_NAME,
            },
        ) as root_span:
            try:
                self._run_stage("ingest", self._stage_ingest)
                self._run_stage("spark_transform", self._stage_spark_transform)
                self._run_stage("lineage", self._stage_lineage)

                total = round(time.time() - self._pipeline_start, 3)
                root_span.set_attribute("pipeline.total_duration_seconds", total)
                root_span.set_status(trace.StatusCode.OK)
                logger.info("[Pipeline] Run %s completed in %.2fs", self.run_id, total)

            except Exception as exc:
                root_span.record_exception(exc)
                root_span.set_status(trace.StatusCode.ERROR, str(exc))
                logger.error("[Pipeline] Run %s FAILED: %s", self.run_id, exc)
                logger.error(traceback.format_exc())
                raise
            finally:
                self._shutdown_otel()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = DataObsPipelineRunner(tenant="poc")
    runner.run()
