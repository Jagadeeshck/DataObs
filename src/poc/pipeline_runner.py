"""
DataObs POC pipeline runner.

The runner keeps the Elastic APM default telemetry path introduced by this
PR, while preserving the resilience work merged on ``main``:
  * uses Elastic APM when available, otherwise no-op telemetry
  * writes to Elasticsearch when reachable, otherwise uses an in-memory sink
  * uses Spark when available, otherwise runs the same transform in Python
  * emits the extra dataset ETL + observability stages only when Elasticsearch
    is the active sink
"""

from __future__ import annotations

import importlib.util
import logging
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol

from src.poc.apm import ApmTelemetry, build_default_apm

logger = logging.getLogger(__name__)

REQUIRED_ROAD_SAFETY_INDICES = {
    "dataobs-rs-accident-facts",
    "dataobs-rs-authority-risk-summary",
    "dataobs-rs-road-risk-summary",
    "dataobs-rs-vehicle-risk-summary",
    "dataobs-rs-casualty-severity-summary",
}


def _env_or_default(*names: str, default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


try:
    from elastic_transport import ConnectionError as ElasticTransportConnectionError
    from elastic_transport import ConnectionTimeout as ElasticTransportConnectionTimeout
except ImportError:  # pragma: no cover - elasticsearch is optional in tests.
    class ElasticTransportConnectionError(Exception):
        pass

    class ElasticTransportConnectionTimeout(Exception):
        pass

try:
    from py4j.protocol import Py4JError
except ImportError:  # pragma: no cover - py4j is optional in tests.
    class Py4JError(RuntimeError):
        pass


try:
    from pyspark.errors import PySparkException
except ImportError:  # pragma: no cover - pyspark is optional in tests.
    class PySparkException(RuntimeError):
        pass


ES_HOST = _env_or_default("ELASTICHOST", "ELASTICSEARCH_URL", default="http://es01:9200")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "changeme")
ES_USER = _env_or_default(
    "ELASTIC_USERNAME",
    "ELASTICSEARCH_USER",
    "ELASTIC_USER",
    default="elastic",
)


def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _otel_sdk_enabled() -> bool:
    return os.environ.get("OTEL_SDK_DISABLED", "true").lower() != "true"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_scenario_fields(doc: Dict[str, Any], run_id: str, run_mode: str) -> Dict[str, Any]:
    out = dict(doc)
    out.setdefault("@timestamp", _utc_now())
    out["run_id"] = run_id
    out["run_mode"] = run_mode
    out["scenario"] = "road_safety"
    return out


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

        self.es = Elasticsearch(
            host,
            basic_auth=(user, password),
            verify_certs=False,
            request_timeout=30,
        )

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


class DataObsPipelineRunner:
    SERVICE_NAME = "dataobs-poc-pipeline"

    def __init__(
        self,
        tenant: str = "poc",
        run_id: Optional[str] = None,
        sink: Optional[PipelineSink] = None,
    ) -> None:
        self.tenant = tenant
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._sink = sink
        self._apm: ApmTelemetry = build_default_apm()
        self._pipeline_start = 0.0
        self._etl_summaries: List[Dict[str, Any]] = []
        self.last_summary: Dict[str, Any] = {}

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
        except (
            ConnectionError,
            ElasticTransportConnectionError,
            ElasticTransportConnectionTimeout,
            ImportError,
            OSError,
            TimeoutError,
            ValueError,
        ) as exc:
            if mode == "elasticsearch":
                raise
            logger.warning(
                "[Pipeline] Elasticsearch unavailable (%s); using in-memory sink.",
                exc,
            )
            self._sink = InMemoryPipelineSink()
            return self._sink

    def _run_stage(
        self,
        name: str,
        fn: Callable[[], Any],
        attrs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        start = time.time()
        labels = {
            "stage": name,
            "tenant": self.tenant,
            "run_id": self.run_id,
            **(attrs or {}),
        }
        try:
            with self._apm.stage(name, span_type=f"pipeline.{name}", labels=labels):
                result = fn()
            duration = time.time() - start
            logger.info("[Pipeline] Stage '%s' completed in %.2fs", name, duration)
            return result
        except Exception as exc:
            duration = time.time() - start
            self._apm.capture_exception()
            logger.error(
                "[Pipeline] Stage '%s' failed after %.2fs: %s",
                name,
                duration,
                exc,
            )
            raise

    def _stage_dataset_etl(self) -> list[Dict[str, Any]]:
        if not isinstance(self._resolve_sink(), ElasticsearchPipelineSink):
            logger.info(
                "[Pipeline] dataset_etl skipped: Elasticsearch sink not active."
            )
            return []

        from src.poc.datasets import resolve_sources
        from src.poc.etl import DatasetETL

        poc_cfg: Dict[str, Any] = {
            "data_sources": [],
            "source_defaults": {
                "enabled": True,
                "auto_discover_if_empty": True,
                "max_datasets": 3,
            },
        }
        sources = resolve_sources(poc_cfg)
        if not sources:
            logger.error("[Pipeline] dataset_etl: no sources resolved — skipping")
            return []

        etl = DatasetETL(
            es_host=ES_HOST,
            es_user=ES_USER,
            es_pass=ES_PASS,
            index_prefix="dataobs-raw",
            max_rows=int(os.environ.get("ETL_MAX_ROWS", "50000")),
        )
        summaries = etl.ingest_all(sources, run_id=self.run_id)
        etl.write_ingest_summary(summaries, run_id=self.run_id, tenant=self.tenant)
        self._etl_summaries = summaries

        total_rows = sum(s["rows_ingested"] for s in summaries)
        self._apm.label(etl_datasets=len(summaries), etl_total_rows=total_rows)
        logger.info(
            "[Pipeline] dataset_etl complete: %d datasets, %d total rows",
            len(summaries),
            total_rows,
        )
        return summaries

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
        self._apm.label(ingest_rows=rows)
        logger.info("[Pipeline] Ingested %d test records", rows)
        return rows

    def _stage_spark_transform(self) -> int:
        mode = os.environ.get("DATAOBS_POC_SPARK_MODE", "auto").lower()
        if mode == "mock":
            return self._stage_mock_transform(write_results=True)

        spark = None
        if not (_module_available("pyspark") and _module_available("pyspark.sql")):
            if mode == "spark":
                raise RuntimeError(
                    "Spark mode requested, but PySpark dependencies are unavailable"
                )
            logger.warning(
                "[Pipeline] PySpark not available; running mock transform."
            )
            return self._stage_mock_transform(write_results=True)

        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from src.poc.spark_instrumentation import SparkApmInstrumentation

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

            with SparkApmInstrumentation(
                spark,
                apm=self._apm,
                job_name=f"dataobs-transform-{self.run_id}",
                extra_labels={"pipeline.run_id": self.run_id},
            ) as sapm:
                with sapm.stage("read_input", labels={"data.source": "inline"}):
                    df = spark.createDataFrame(
                        [(i, float(i * 1.5), self.run_id) for i in range(100)],
                        ["record_id", "value", "run_id"],
                    )

                with sapm.stage(
                    "transform",
                    labels={"transform.type": "filter_aggregate"},
                ):
                    df_transformed = (
                        df.filter(F.col("value") > 10)
                        .withColumn("value_doubled", F.col("value") * 2)
                        .withColumn("processed_at", F.lit(_utc_now()))
                    )

                with sapm.stage(
                    "quality_check",
                    labels={"quality.rule": "null_check"},
                ):
                    null_count = df_transformed.filter(F.col("value").isNull()).count()
                    row_count = df_transformed.count()
                    quality_score = 100.0 if null_count == 0 else round(
                        (1 - null_count / row_count) * 100,
                        2,
                    )
                    self._apm.label(
                        quality_score=quality_score,
                        null_count=null_count,
                        row_count=row_count,
                    )
                    logger.info(
                        "[Pipeline] Quality check: %d rows, %d nulls, score=%.1f",
                        row_count,
                        null_count,
                        quality_score,
                    )

                with sapm.stage(
                    "write_output",
                    labels={"data.sink": type(self._resolve_sink()).__name__},
                ):
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

                sapm.emit_metrics(df_transformed, stage="transform")

            logger.info("[Pipeline] Spark transform stage complete")
            return row_count
        except (OSError, Py4JError, PySparkException, RuntimeError) as exc:
            if mode == "spark":
                raise
            logger.warning(
                "[Pipeline] Spark unavailable or failed (%s); running mock transform.",
                exc,
            )
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
        self._apm.label(mock_rows=len(docs))
        logger.info("[Pipeline] Mock transform: %d rows", len(docs))
        return len(docs)

    def _stage_lineage(self) -> None:
        self._resolve_sink().index_lineage(
            {
                "@timestamp": _utc_now(),
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
        )
        for summary in self._etl_summaries:
            self._resolve_sink().index_lineage(
                {
                    "@timestamp": _utc_now(),
                    "run_id": self.run_id,
                    "tenant": self.tenant,
                    "source": summary.get("source_url", summary["dataset"]),
                    "target": summary["index"],
                    "source_index": "external-url",
                    "sink_index": summary["index"],
                    "pipeline": self.SERVICE_NAME,
                    "lineage_type": "ingest",
                    "relation": "ingest",
                    "row_count": summary["rows_ingested"],
                    "dataset": summary["dataset"],
                    "theme": summary.get("theme", "unknown"),
                    "status": summary.get("status", "ok"),
                }
            )
        logger.info("[Pipeline] Lineage events written to dataobs-lineage")

    def _stage_observability(self) -> None:
        if not isinstance(self._resolve_sink(), ElasticsearchPipelineSink):
            logger.info(
                "[Pipeline] observability skipped: Elasticsearch sink not active."
            )
            return

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
        for summary in self._etl_summaries:
            if summary["status"] != "ok":
                continue
            ow.register_asset(
                asset_id=summary["index"],
                name=summary["index"],
                asset_type="elasticsearch_index",
                platform="elasticsearch",
                location=f"{ES_HOST}/{summary['index']}",
                tags=["poc", "raw", "etl", summary.get("theme", "unknown")],
                row_count=summary["rows_ingested"],
                column_count=summary.get("columns", 0),
                reliability_score=99.0,
            )
            ow.emit_volume(
                asset_id=summary["index"],
                asset_name=summary["index"],
                row_count=summary["rows_ingested"],
                expected_min=1,
                expected_max=100_000,
            )
            ow.emit_freshness(
                asset_id=summary["index"],
                asset_name=summary["index"],
                last_seen=_utc_now(),
                lag_seconds=int(summary["duration_seconds"]),
                sla_seconds=3600,
            )

        ow.emit_quality_check(
            run_id=self.run_id,
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            check_name="row_count_min",
            check_type="volume",
            column=None,
            value=100.0,
            threshold=10.0,
            status="pass",
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
            value=100.0,
            threshold=99.0,
            status="pass",
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
            value=2.0,
            threshold=0.0,
            status="warn",
            severity="warning",
            expression="duplicate_count(record_id) == 0",
            score=98.0,
            message="2 duplicate record_id values detected",
        )
        ow.emit_freshness(
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            last_seen=_utc_now(),
            lag_seconds=30,
            sla_seconds=1800,
        )
        ow.emit_freshness(
            asset_id="dataobs-test-data",
            asset_name="dataobs-test-data",
            last_seen=_utc_now(),
            lag_seconds=7200,
            sla_seconds=3600,
        )
        ow.emit_volume(
            asset_id="dataobs-spark-results",
            asset_name="dataobs-spark-results",
            row_count=100,
            expected_min=80,
            expected_max=120,
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
        logger.info(
            "[Pipeline] Observability docs emitted "
            "(assets/quality/freshness/volume/schema/lineage/alerts)"
        )

    def run(self) -> Dict[str, Any]:
        self._bootstrap_telemetry()
        self._pipeline_start = time.time()
        summary: Dict[str, Any] = {"run_id": self.run_id, "tenant": self.tenant}
        scenario = os.environ.get("DATAOBS_DEMO_SCENARIO", "").strip().lower()
        if scenario == "road_safety":
            from pathlib import Path
            from src.poc.scenarios.road_safety.generator import generate_scaled
            from src.poc.scenarios.road_safety.pipeline import run_road_safety_scenario
            scale = os.environ.get("DATAOBS_DEMO_SCALE", "small").lower()
            run_mode = os.environ.get("DATAOBS_DEMO_RUN_MODE", "good").lower()
            logger.info("[Pipeline][road_safety] DATAOBS_DEMO_SCENARIO=%s", scenario)
            logger.info("[Pipeline][road_safety] DATAOBS_DEMO_RUN_MODE=%s", run_mode)
            logger.info("[Pipeline][road_safety] DATAOBS_DEMO_SCALE=%s", scale)
            seed_dir = Path("fixtures/poc/road_safety")
            data_dir = Path("/tmp/dataobs/tmp/road_safety") / f"{self.run_id}-{scale}"
            generated = generate_scaled(seed_dir, data_dir, scale=scale)
            logger.info("[Pipeline][road_safety] Generated fixture files: %s", {k: str(v) for k, v in generated.items()})
            result = run_road_safety_scenario(data_dir, self.run_id, run_mode=run_mode)

            outputs = result.get("outputs", {})
            missing = sorted(REQUIRED_ROAD_SAFETY_INDICES - set(outputs.keys()))
            if missing:
                raise RuntimeError(f"Road safety scenario missing required output indices: {missing}")
            empty = sorted([name for name, docs in outputs.items() if not docs])
            if empty:
                raise RuntimeError(f"Road safety scenario returned empty outputs for indices: {empty}")
            if not result.get("spark_metrics"):
                raise RuntimeError("Road safety scenario returned no spark_metrics")

            output_counts = {name: len(docs) for name, docs in outputs.items()}
            logger.info("[Pipeline][road_safety] Output index counts: %s", output_counts)
            logger.info("[Pipeline][road_safety] Spark metrics count: %s", len(result["spark_metrics"]))

            if isinstance(self._resolve_sink(), ElasticsearchPipelineSink):
                from elasticsearch import Elasticsearch
                es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASS), verify_certs=False)
                for index, docs in outputs.items():
                    for d in docs:
                        es.index(index=index, document=_ensure_scenario_fields(d, self.run_id, run_mode))
                for q in result["quality"]:
                    q_doc = _ensure_scenario_fields(q, self.run_id, run_mode)
                    es.index(index="dataobs-quality", document=q_doc)
                    if q["status"] != "pass":
                        es.index(index="dataobs-alerts", document=_ensure_scenario_fields({"source": "quality", "severity": "high", "check_name": q["check_name"]}, self.run_id, run_mode))
                        es.index(index="dataobs-schema", document=_ensure_scenario_fields({"status": "drift", "check_name": q["check_name"]}, self.run_id, run_mode))
                        es.index(index="dataobs-volume", document=_ensure_scenario_fields({"status": "anomaly", "check_name": q["check_name"]}, self.run_id, run_mode))
                        es.index(index="dataobs-freshness", document=_ensure_scenario_fields({"status": "stale", "check_name": q["check_name"]}, self.run_id, run_mode))
                for m in result["spark_metrics"]:
                    es.index(index="dataobs-spark-metrics", document=_ensure_scenario_fields(m, self.run_id, run_mode))
                es.index(index="dataobs-lineage", document=_ensure_scenario_fields({"source": "road_safety_raw", "target": "dataobs-rs-accident-facts", "relation": "transformation"}, self.run_id, run_mode))
            summary["scenario"] = "road_safety"
            summary["scale"] = scale
            summary["run_mode"] = run_mode
            summary["generated_files"] = {k: str(v) for k, v in generated.items()}
            summary["duration_seconds"] = round(time.time() - self._pipeline_start, 3)
            self.last_summary = summary
            self._shutdown_telemetry()
            return summary

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
                summary["etl_datasets"] = len(
                    self._run_stage("dataset_etl", self._stage_dataset_etl)
                )
                summary["ingested_rows"] = self._run_stage("ingest", self._stage_ingest)
                summary["transformed_rows"] = self._run_stage(
                    "spark_transform",
                    self._stage_spark_transform,
                )
                self._run_stage("lineage", self._stage_lineage)
                self._run_stage("observability", self._stage_observability)
                summary["duration_seconds"] = round(
                    time.time() - self._pipeline_start,
                    3,
                )
                summary["sink"] = type(self._resolve_sink()).__name__
                self._apm.label(pipeline_total_seconds=summary["duration_seconds"])
                logger.info("[Pipeline] Run %s completed: %s", self.run_id, summary)
                self.last_summary = summary
                return summary
        except Exception as exc:
            logger.error("[Pipeline] Run %s FAILED: %s", self.run_id, exc)
            logger.error(traceback.format_exc())
            raise
        finally:
            self._shutdown_telemetry()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    DataObsPipelineRunner(
        tenant=os.environ.get("DATAOBS_TENANT_ID", "poc")
    ).run()
