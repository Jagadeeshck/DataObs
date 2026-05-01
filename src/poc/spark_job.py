"""
DataObs POC — main Spark pipeline entry point.

Pipeline stages
---------------
  1. discover   — resolve data sources (explicit config or auto data.gov.uk)
  2. download   — fetch raw files to local working directory
  3. parse      — read CSV/JSON into Python dicts; attach ingestion metadata
  4. transform  — load into Spark, normalise columns, cap at 5,000 rows
  5. quality    — run baseline checks (row count, nulls, duplicates, schema)
  6. load       — bulk-index raw, curated, quality, lineage into Elasticsearch
  7. complete   — summary log with counts per dataset

All stages emit telemetry via TelemetryEmitter (OTel SDK or logger fallback).
Run with::

    PYTHONPATH=. python -m src.poc.spark_job

Or via the convenience script::

    ./scripts/run_poc_pipeline.sh
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from requests import HTTPError, RequestException
from src.poc.config import ensure_dirs, get_poc_config
from src.poc.datasets import resolve_sources
from src.poc.es_writer import POCElasticWriter
from src.poc.quality import run_basic_quality_checks
from src.poc.telemetry import TelemetryEmitter

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_spark(master: str):
    from pyspark.sql import SparkSession
    return (
        SparkSession.builder
        .appName("dataobs-poc-pipeline")
        .master(master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.extraJavaOptions", "-Dlog4j.logLevel=WARN")
        .getOrCreate()
    )


def _download(url: str, target: Path, timeout: int = 120) -> None:
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    with open(target, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=65536):
            fh.write(chunk)
    logger.info("[download] Saved %s bytes → %s", target.stat().st_size, target)


def _parse(path: Path, fmt: str) -> List[Dict[str, Any]]:
    fmt = fmt.lower().strip(".")
    raw = path.read_bytes()
    if fmt == "csv":
        text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]
    if fmt == "json":
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("result", "data", "records", "rows"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            return [payload]
    logger.warning("[parse] Unsupported format '%s' — returning empty list.", fmt)
    return []


def _normalize(records: List[Dict[str, Any]], dataset_name: str, source_url: str) -> List[Dict[str, Any]]:
    ts = _now()
    out = []
    for row in records:
        doc = {k.strip().lower().replace(" ", "_").replace("-", "_"): v for k, v in row.items()}
        doc["dataset"] = dataset_name
        doc["source_url"] = source_url
        doc["pipeline_name"] = "dataobs-poc"
        doc["dataset_name"] = dataset_name
        doc["@timestamp"] = ts
        out.append(doc)
    return out


def _spark_transform(spark, records: List[Dict[str, Any]], limit: int = 5000) -> List[Dict[str, Any]]:
    from pyspark.sql.functions import lit
    if not records:
        return []
    df = spark.createDataFrame(records)
    df = df.withColumn("_pipeline_version", lit("poc-v1"))
    collected = df.limit(limit).collect()
    return [row.asDict(recursive=True) for row in collected]


def main() -> None:
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    poc_cfg = get_poc_config()
    if not poc_cfg.get("enabled", False):
        logger.info("POC mode is disabled (poc.enabled: false). Set to true in config/dataobs.yaml.")
        return

    ensure_dirs(poc_cfg)

    otel_cfg = poc_cfg.get("opentelemetry", {})
    telemetry = TelemetryEmitter(
        service_name=otel_cfg.get("service_name", "dataobs-poc-pipeline"),
        otlp_endpoint=otel_cfg.get("exporter_otlp_endpoint"),
    )

    writer = POCElasticWriter(poc_cfg)
    runtime = poc_cfg["runtime"]
    raw_dir = Path(runtime["raw_download_dir"])

    # ── 1. Discover sources ─────────────────────────────────────────────────
    with telemetry.stage("discover"):
        sources = resolve_sources(poc_cfg)
        if not sources:
            raise RuntimeError(
                "No data sources resolved. Set poc.data_sources in config or "
                "enable poc.source_defaults.auto_discover_if_empty."
            )
        logger.info("[discover] %d source(s) resolved.", len(sources))

    # ── Ensure ES indices ───────────────────────────────────────────────────
    writer.ensure_indices()

    spark = _build_spark(runtime["spark_master"])
    total_ingested = 0
    quality_rule_cfg = poc_cfg.get("processing", {}).get("quality_rules", {})
    failed_datasets: List[Dict[str, Any]] = []

    try:
        for source in sources:
            dataset_name = source.get("name") or source.get("poc_name") or source.get("dataset_id", "unknown")
            fmt = (source.get("format") or "csv").lower()
            ext = "json" if fmt == "json" else "csv"
            local_path = raw_dir / f"{dataset_name}.{ext}"
            url = source["resource_url"]
            current_stage = "download"

            try:
                # ── 2. Download ─────────────────────────────────────────────
                with telemetry.stage("download", dataset=dataset_name, url=url):
                    _download(url, local_path)

                # ── 3. Parse ────────────────────────────────────────────────
                current_stage = "parse"
                with telemetry.stage("parse", dataset=dataset_name, format=fmt):
                    records = _parse(local_path, fmt)
                    logger.info("[parse] %d rows parsed from %s", len(records), dataset_name)

                # ── 4. Spark transform ──────────────────────────────────────
                current_stage = "transform"
                with telemetry.stage("transform", dataset=dataset_name, rows_in=len(records)):
                    raw_annotated = _normalize(records, dataset_name, url)
                    curated = _spark_transform(spark, raw_annotated, limit=5000)

                # ── 5. Quality checks ───────────────────────────────────────
                current_stage = "quality_check"
                with telemetry.stage("quality_check", dataset=dataset_name):
                    quality_results = run_basic_quality_checks(
                        curated,
                        dataset_name,
                        warn_null_pct=float(quality_rule_cfg.get("max_null_pct_warn", 5.0)),
                        fail_null_pct=float(quality_rule_cfg.get("max_null_pct_fail", 20.0)),
                        dup_threshold_pct=float(quality_rule_cfg.get("duplicate_threshold_pct", 1.0)),
                    )
                    for qr in quality_results:
                        telemetry.emit_quality_event(
                            dataset_name,
                            qr["status"],
                            check_name=qr["check_name"],
                            score=qr.get("score", 0),
                        )

                # ── 6. Load into Elasticsearch ──────────────────────────────
                current_stage = "load_elasticsearch"
                with telemetry.stage("load_elasticsearch", dataset=dataset_name):
                    writer.write_raw(raw_annotated[:5000])
                    writer.write_curated(curated)
                    writer.write_quality(quality_results)
                    writer.write_lineage([
                        {
                            "source": url,
                            "target": dataset_name,
                            "relation": "ingested_from",
                            "dataset": dataset_name,
                            "@timestamp": _now(),
                        },
                        {
                            "source": dataset_name,
                            "target": f"{dataset_name}_curated",
                            "relation": "transformed_to",
                            "dataset": dataset_name,
                            "@timestamp": _now(),
                        },
                    ])
                    telemetry.emit_metric("records_ingested", len(curated), dataset=dataset_name)
                    telemetry.emit_lineage(url, dataset_name, relation="ingested_from")
                    telemetry.emit_lineage(dataset_name, f"{dataset_name}_curated", relation="transformed_to")
                    total_ingested += len(curated)

            except (HTTPError, RequestException, Exception) as exc:
                failed_datasets.append({
                    "dataset": dataset_name,
                    "url": url,
                    "error": str(exc),
                    "stage": current_stage,
                    "@timestamp": _now(),
                })

                logger.exception(
                    "[resilience] Dataset failed but pipeline will continue: %s (%s) at stage=%s",
                    dataset_name,
                    url,
                    current_stage,
                )

                telemetry.emit_metric(
                    "dataset_failed",
                    1,
                    dataset=dataset_name,
                    stage=current_stage,
                )
                continue

    finally:
        spark.stop()

    logger.info(
        "[complete] POC pipeline finished. Datasets discovered: %d | Failed: %d | Total records ingested: %d",
        len(sources),
        len(failed_datasets),
        total_ingested,
    )

    if failed_datasets:
        for item in failed_datasets:
            logger.warning(
                "[complete][failed_dataset] dataset=%s stage=%s url=%s error=%s",
                item["dataset"],
                item["stage"],
                item["url"],
                item["error"],
            )


if __name__ == "__main__":
    main()