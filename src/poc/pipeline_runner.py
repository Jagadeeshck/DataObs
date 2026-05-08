"""
src/poc/pipeline_runner.py
──────────────────────────
Full DataObs POC pipeline runner.

Default telemetry path: **Elastic APM**.
  - Root transaction wraps the whole run.
  - Each stage (ingest, spark_transform, lineage, observability) becomes
    a child span via the Elastic APM Python agent.
  - Custom labels capture run_id / tenant / dataset.
  - Telemetry ships to the APM Server hosted by the Fleet-managed
    elastic-agent container at ``http://elastic-agent:8200``.

Optional OTel mode: enabled by setting ``OTEL_SDK_DISABLED=false`` AND
running with ``docker compose --profile otel`` so that a standalone
collector exists. When this mode is off (the POC default), the OTel
SDK is never imported and the pipeline never tries to dial an OTLP
endpoint, which prevents the
``NameResolutionError(host='otel-collector', port=4318)`` retry-spam
that previously appeared in the logs.

Direct Elasticsearch indexing for the dataobs-* documents
(assets/quality/freshness/volume/schema/lineage/alerts) and the raw
+ curated POC data is unchanged.
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from src.poc.apm import ApmTelemetry, build_default_apm

logger = logging.getLogger(__name__)

ES_HOST = os.environ.get("ELASTICHOST", "http://es01:9200")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "changeme")

# Data-observability indices (also defined in config/dataobs_poc.yaml).
IDX_ASSETS    = "dataobs-assets"
IDX_QUALITY   = "dataobs-quality"
IDX_FRESHNESS = "dataobs-freshness"
IDX_VOLUME    = "dataobs-volume"
IDX_SCHEMA    = "dataobs-schema"
IDX_LINEAGE   = "dataobs-lineage"
IDX_ALERTS    = "dataobs-alerts"
IDX_CURATED   = "dataobs-poc-curated"
IDX_RAW       = "dataobs-poc-raw"


def _otel_sdk_enabled() -> bool:
    """OTel SDK is opt-in for the POC; default is disabled."""
    return os.environ.get("OTEL_SDK_DISABLED", "true").lower() != "true"


class DataObsPipelineRunner:
    """
    Orchestrates the DataObs POC pipeline with full Elastic APM
    instrumentation. Every stage emits a span/transaction visible in
    Kibana APM UI; raw + curated rows and the dataobs-* observability
    docs are indexed directly into Elasticsearch.
    """

    SERVICE_NAME = "dataobs-poc-pipeline"

    def __init__(self, tenant: str = "poc", run_id: Optional[str] = None):
        self.tenant = tenant
        self.run_id = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self._apm: ApmTelemetry = build_default_apm()
        self._pipeline_start: float = 0.0

    # ── Bootstrap ──────────────────────────────────────────────────────────
    def _bootstrap_telemetry(self) -> None:
        self._apm.start()
        self._apm.label(
            run_id=self.run_id,
            tenant=self.tenant,
            service_name=self.SERVICE_NAME,
            telemetry_path="elastic-apm",
        )
        if _otel_sdk_enabled():
            logger.info(
                "[Pipeline] OTEL_SDK_DISABLED=false detected — the optional "
                "OTel collector path is enabled (you must also start the "
                "`otel` Compose profile)."
            )
        else:
            logger.info(
                "[Pipeline] OTel SDK disabled (default). Telemetry path = "
                "Elastic APM Python agent → Elastic APM Server."
            )

    def _shutdown_telemetry(self) -> None:
        self._apm.shutdown()

    # ── Stage runner ───────────────────────────────────────────────────────
    def _run_stage(
        self,
        name: str,
        fn,
        attrs: Dict[str, Any] = {},
    ):
        """Execute fn() inside an APM span, recording labels + duration."""
        t0 = time.time()
        labels = {
            "stage": name,
            "tenant": self.tenant,
            "run_id": self.run_id,
            **attrs,
        }
        try:
            with self._apm.stage(name, span_type=f"pipeline.{name}", labels=labels):
                result = fn()
            duration = time.time() - t0
            logger.info("[Pipeline] Stage '%s' completed in %.2fs", name, duration)
            return result
        except Exception as exc:
            duration = time.time() - t0
            self._apm.capture_exception()
            logger.error(
                "[Pipeline] Stage '%s' failed after %.2fs: %s",
                name, duration, exc,
            )
            raise

    # ── Pipeline stages ────────────────────────────────────────────────────
    def _stage_ingest(self):
        from elasticsearch import Elasticsearch
        es = Elasticsearch(ES_HOST, basic_auth=("elastic", ES_PASS), verify_certs=False)
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
        self._apm.label(ingest_rows=rows)
        logger.info("[Pipeline] Ingested %d test records", rows)
        return rows

    def _stage_spark_transform(self):
        try:
            from pyspark.sql import SparkSession
            from src.poc.spark_instrumentation import SparkApmInstrumentation

            spark = (
                SparkSession.builder
                .appName(f"DataObs-POC-{self.run_id}")
                .master(os.environ.get("SPARK_MASTER", "local[*]"))
                .config("spark.driver.memory", "512m")
                .config("spark.executor.memory", "512m")
                .config(
                    "spark.jars.packages",
                    "org.apache.spark:spark-sql_2.12:3.4.3",
                )
                .getOrCreate()
            )

            with SparkApmInstrumentation(
                spark,
                apm=self._apm,
                job_name=f"dataobs-transform-{self.run_id}",
            ) as sapm:
                with sapm.stage("read_input", labels={"data.source": "inline"}):
                    data = [(i, float(i * 1.5), self.run_id) for i in range(100)]
                    schema = ["record_id", "value", "run_id"]
                    df = spark.createDataFrame(data, schema=schema)

                with sapm.stage("transform", labels={"transform.type": "filter_aggregate"}):
                    from pyspark.sql import functions as F
                    df_transformed = (
                        df.filter(F.col("value") > 10)
                        .withColumn("value_doubled", F.col("value") * 2)
                        .withColumn("processed_at", F.lit(datetime.utcnow().isoformat()))
                    )

                with sapm.stage("quality_check", labels={"quality.rule": "null_check"}):
                    null_count = df_transformed.filter(F.col("value").isNull()).count()
                    row_count = df_transformed.count()
                    quality_score = 100.0 if null_count == 0 else round(
                        (1 - null_count / row_count) * 100, 2
                    )
                    self._apm.label(
                        quality_score=quality_score,
                        null_count=null_count,
                        row_count=row_count,
                    )
                    logger.info(
                        "[Pipeline] Quality check: %d rows, %d nulls, score=%.1f",
                        row_count, null_count, quality_score,
                    )

                with sapm.stage("write_output", labels={"data.sink": "elasticsearch"}):
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

                sapm.emit_metrics(df_transformed, stage="transform")

            spark.stop()
            logger.info("[Pipeline] Spark transform stage complete")
            return row_count

        except ImportError as exc:
            logger.warning(
                "[Pipeline] PySpark not available (%s) — running mock transform", exc
            )
            return self._stage_mock_transform()

    def _stage_mock_transform(self) -> int:
        rows = 100
        mock_results = [
            {"record_id": i, "value": i * 1.5, "value_doubled": i * 3.0}
            for i in range(rows)
            if i * 1.5 > 10
        ]
        self._apm.label(mock_rows=len(mock_results))
        logger.info("[Pipeline] Mock transform: %d rows", len(mock_results))
        return len(mock_results)

    def _stage_lineage(self):
        from elasticsearch import Elasticsearch
        es = Elasticsearch(ES_HOST, basic_auth=("elastic", ES_PASS), verify_certs=False)
        lineage_doc = {
            "@timestamp": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "tenant": self.tenant,
            "source": "dataobs-test-data",
            "target": "dataobs-spark-results",
            "source_index": "dataobs-test-data",
            "sink_index": "dataobs-spark-results",
            "pipeline": self.SERVICE_NAME,
            "lineage_type": "transformation",
            "relation": "transformation",
            "row_count": 100,
        }
        es.index(index="dataobs-lineage", document=lineage_doc)
        logger.info("[Pipeline] Lineage event written to dataobs-lineage")

    def _stage_observability(self):
        from src.poc.observability_writer import ObservabilityWriter

        ow = ObservabilityWriter(host=ES_HOST, password=ES_PASS, tenant=self.tenant)

        ow.register_asset(
            asset_id="dataobs-test-data",
            name="dataobs-test-data",
            asset_type="elasticsearch_index",
            platform="elasticsearch",
            location=f"{ES_HOST}/dataobs-test-data",
            tags=["poc", "raw", "ingest"],
            row_count=50,
            column_count=5,
            reliability_score=98.0,
        )
        ow.register_asset(
            asset_id="dataobs-spark-results",
            name="dataobs-spark-results",
            asset_type="elasticsearch_index",
            platform="elasticsearch",
            location=f"{ES_HOST}/dataobs-spark-results",
            tags=["poc", "curated", "spark"],
            row_count=100,
            column_count=6,
            reliability_score=99.0,
        )

        ow.emit_quality_check(
            run_id=self.run_id,
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            check_name="row_count_min",
            check_type="volume",
            column=None,
            value=100.0, threshold=10.0, status="pass",
            expression="row_count >= 10",
            score=100.0,
            message="Row count above minimum",
        )
        ow.emit_quality_check(
            run_id=self.run_id,
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            check_name="value_not_null",
            check_type="completeness",
            column="value",
            value=100.0, threshold=99.0, status="pass",
            expression="not_null(value) >= 99%",
            score=100.0,
            message="No null values detected",
        )
        ow.emit_quality_check(
            run_id=self.run_id,
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            check_name="record_id_unique",
            check_type="uniqueness",
            column="record_id",
            value=2.0, threshold=0.0, status="warn",
            severity="warning",
            expression="duplicate_count(record_id) == 0",
            score=98.0,
            message="2 duplicate record_id values detected",
        )

        ow.emit_freshness(
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            last_seen=datetime.utcnow().isoformat(),
            lag_seconds=30,
            sla_seconds=1800,
        )
        ow.emit_freshness(
            asset_id="dataobs-test-data",
            asset_name="dataobs-test-data",
            last_seen=datetime.utcnow().isoformat(),
            lag_seconds=7200,
            sla_seconds=3600,
        )

        ow.emit_volume(
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            row_count=100, expected_min=80, expected_max=120,
        )

        ow.snapshot_schema(
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            columns=[
                {"name": "record_id", "type": "long"},
                {"name": "value", "type": "double"},
                {"name": "value_doubled", "type": "double"},
                {"name": "run_id", "type": "keyword"},
                {"name": "processed_at", "type": "date"},
            ],
        )

        ow.emit_lineage(
            run_id=self.run_id,
            source="dataobs-test-data",
            target="dataobs-spark-results",
            relation="transformation",
            pipeline=self.SERVICE_NAME,
            row_count=100,
            fields=[
                {"source": "value", "target": "value"},
                {"source": "value", "target": "value_doubled"},
                {"source": "record_id", "target": "record_id"},
            ],
        )
        logger.info("[Pipeline] Observability docs emitted (assets/quality/freshness/volume/schema/lineage/alerts)")

    # ── Main run ───────────────────────────────────────────────────────────
    def run(self):
        self._bootstrap_telemetry()
        self._pipeline_start = time.time()

        try:
            with self._apm.transaction(
                name=f"pipeline.run.{self.tenant}",
                transaction_type="pipeline",
                labels={
                    "run_id": self.run_id,
                    "tenant": self.tenant,
                    "service.name": self.SERVICE_NAME,
                },
            ):
                self._run_stage("ingest", self._stage_ingest)
                self._run_stage("spark_transform", self._stage_spark_transform)
                self._run_stage("lineage", self._stage_lineage)
                self._run_stage("observability", self._stage_observability)

                total = round(time.time() - self._pipeline_start, 3)
                self._apm.label(pipeline_total_seconds=total)
                logger.info("[Pipeline] Run %s completed in %.2fs", self.run_id, total)
        except Exception as exc:
            logger.error("[Pipeline] Run %s FAILED: %s", self.run_id, exc)
            logger.error(traceback.format_exc())
            raise
        finally:
            self._shutdown_telemetry()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = DataObsPipelineRunner(tenant="poc")
    runner.run()
