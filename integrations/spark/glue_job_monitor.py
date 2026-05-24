"""
AWS Glue job-run monitor with OpenTelemetry spans/metrics and failure alert routing.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import boto3
import yaml
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from src.alerting.pagerduty import PagerDutyClient, PagerDutyConfig, PagerDutyEvent
from src.alerting.slack import SlackClient, SlackConfig, SlackEvent

logger = logging.getLogger(__name__)

_CRITICAL_PD_CATEGORIES = frozenset({"OUT_OF_MEMORY_ERROR", "UNCLASSIFIED_SPARK_ERROR"})
_VALID_GLUE_ERROR_CATEGORIES = frozenset({
    "OUT_OF_MEMORY_ERROR",
    "PERMISSION_ERROR",
    "CONNECTION_ERROR",
    "RESOURCE_NOT_FOUND_ERROR",
    "THROTTLING_ERROR",
    "SYNTAX_ERROR",
    "GLUE_OPERATION_TIMEOUT_ERROR",
    "S3_ERROR",
    "UNCLASSIFIED_SPARK_ERROR",
})


@dataclass(frozen=True)
class GlueMonitorThresholds:
    heap_used_pct_critical: float = 90.0
    cpu_load_warn: float = 0.85
    skewness_warn: float = 2.0
    worker_utilization_warn: float = 0.95
    disk_used_pct_warn: float = 80.0


def _setup_glue_otel_provider(service_name: str = "dataobs-glue-monitor", export_timeout_ms: int = 30_000) -> None:
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource.create({"service.name": service_name, "service.namespace": "dataobs"})
    timeout_seconds = max(1, export_timeout_ms // 1000)

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint, timeout=timeout_seconds),
            max_queue_size=4096,
            max_export_batch_size=512,
            export_timeout_millis=export_timeout_ms,
        )
    )
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, timeout=timeout_seconds),
                export_interval_millis=30_000,
                export_timeout_millis=export_timeout_ms,
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)


def _load_glue_thresholds(config_path: str | None = None) -> GlueMonitorThresholds:
    path = Path(config_path or os.getenv("DATAOBS_CONFIG", "config/dataobs.yaml"))
    if not path.exists():
        return GlueMonitorThresholds()

    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    section = cfg.get("glue_monitors", {}) if isinstance(cfg, dict) else {}
    return GlueMonitorThresholds(
        heap_used_pct_critical=float(section.get("heap_used_pct_critical", 90)),
        cpu_load_warn=float(section.get("cpu_load_warn", 0.85)),
        skewness_warn=float(section.get("skewness_warn", 2.0)),
        worker_utilization_warn=float(section.get("worker_utilization_warn", 0.95)),
        disk_used_pct_warn=float(section.get("disk_used_pct_warn", 80)),
    )


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _duration_seconds(run: dict[str, Any]) -> int:
    explicit = _as_int(run.get("ExecutionTime"), default=-1)
    if explicit >= 0:
        return explicit
    started = run.get("StartedOn")
    completed = run.get("CompletedOn")
    if isinstance(started, datetime) and isinstance(completed, datetime):
        return max(0, int((completed - started).total_seconds()))
    return 0


def _extract_number(run: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in run:
            return _as_float(run.get(key), default=default)

    glue_metrics = run.get("GlueMetrics")
    if isinstance(glue_metrics, dict):
        for key in keys:
            if key in glue_metrics:
                return _as_float(glue_metrics.get(key), default=default)
    return default


def _resolve_job_type(run: dict[str, Any]) -> str:
    command = run.get("JobCommand", {})
    if isinstance(command, dict):
        name = str(command.get("Name", "")).strip().lower()
        if name in {"glueetl", "pythonshell", "gluestreaming"}:
            return name
    return "glueetl"


def _resolve_error_category(run: dict[str, Any]) -> str:
    raw_error = str(run.get("ErrorCode", "") or run.get("ErrorMessage", "") or run.get("StateDetail", "")).upper()
    for known in _VALID_GLUE_ERROR_CATEGORIES:
        if known in raw_error:
            return known

    lowered = raw_error.lower()
    if "outofmemory" in lowered or "out of memory" in lowered or "heap space" in lowered:
        return "OUT_OF_MEMORY_ERROR"
    if "permission" in lowered or "accessdenied" in lowered or "not authorized" in lowered:
        return "PERMISSION_ERROR"
    if "connection" in lowered or "refused" in lowered or "network" in lowered:
        return "CONNECTION_ERROR"
    if "not found" in lowered or "nosuch" in lowered:
        return "RESOURCE_NOT_FOUND_ERROR"
    if "throttl" in lowered:
        return "THROTTLING_ERROR"
    if "syntax" in lowered or "parse" in lowered:
        return "SYNTAX_ERROR"
    if "timeout" in lowered or "timed out" in lowered:
        return "GLUE_OPERATION_TIMEOUT_ERROR"
    if "s3" in lowered or "bucket" in lowered or "key" in lowered:
        return "S3_ERROR"
    return "UNCLASSIFIED_SPARK_ERROR"


class GlueJobMonitor:
    def __init__(
        self,
        job_names: Iterable[str],
        poll_interval_seconds: int = 60,
        glue_client: Any | None = None,
        pagerduty_client: PagerDutyClient | None = None,
        slack_client: SlackClient | None = None,
        config_path: str | None = None,
    ) -> None:
        _setup_glue_otel_provider()
        self._job_names = [n for n in (name.strip() for name in job_names) if n]
        self._poll_interval_seconds = poll_interval_seconds
        self._glue = glue_client or boto3.client("glue", region_name=os.getenv("AWS_REGION"))
        self._seen_run_ids: set[str] = set()
        self._thresholds = _load_glue_thresholds(config_path=config_path)
        self._tracer = trace.get_tracer("dataobs.glue")
        self._meter = metrics.get_meter("dataobs.glue")

        self._heap_used_pct = self._meter.create_gauge("dataobs.glue.driver.memory.heap.used_percentage")
        self._disk_used_pct = self._meter.create_gauge("dataobs.glue.driver.disk.used_percentage")
        self._cpu_load = self._meter.create_gauge("dataobs.glue.driver.system.cpuSystemLoad")
        self._worker_utilization = self._meter.create_gauge("dataobs.glue.driver.workerUtilization")
        self._job_skewness = self._meter.create_gauge("dataobs.glue.driver.skewness.job")
        self._elapsed_time_ms = self._meter.create_histogram("dataobs.glue.job.elapsed_time_ms", unit="ms")
        self._failed_tasks = self._meter.create_counter("dataobs.glue.job.failed_tasks")
        self._failure_count = self._meter.create_counter("dataobs.glue.job.failure_count")

        self._pagerduty = pagerduty_client or self._build_pagerduty_client()
        self._slack = slack_client or self._build_slack_client()

    @staticmethod
    def _build_pagerduty_client() -> PagerDutyClient | None:
        routing_key = os.getenv("PAGERDUTY_ROUTING_KEY", "").strip()
        if not routing_key:
            return None
        return PagerDutyClient(PagerDutyConfig(routing_key=routing_key, source="dataobs-glue-monitor"))

    @staticmethod
    def _build_slack_client() -> SlackClient | None:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        if not webhook_url:
            return None
        return SlackClient(SlackConfig(webhook_url=webhook_url))

    async def run_forever(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self._poll_interval_seconds)

    async def poll_once(self) -> list[str]:
        processed_run_ids: list[str] = []
        for job_name in self._job_names:
            response = self._glue.get_job_runs(JobName=job_name, MaxResults=10)
            for run in response.get("JobRuns", []) or []:
                run_id = str(run.get("Id", "")).strip()
                if not run_id or run_id in self._seen_run_ids:
                    continue
                self._seen_run_ids.add(run_id)
                self._emit_job_run(job_name=job_name, run=run)
                processed_run_ids.append(run_id)
        return processed_run_ids

    def _emit_job_run(self, job_name: str, run: dict[str, Any]) -> None:
        run_id = str(run.get("Id", ""))
        run_state = str(run.get("JobRunState", "RUNNING"))
        worker_count = _as_int(run.get("NumberOfWorkers"), default=_as_int(run.get("MaxCapacity"), default=0))
        worker_type = str(run.get("WorkerType", "G.1X"))
        job_type = _resolve_job_type(run)
        duration_seconds = _duration_seconds(run)
        dpu_seconds = float(worker_count * duration_seconds)
        elapsed_time_ms = _as_float(run.get("ExecutionTime"), default=float(duration_seconds)) * 1000

        records_read = _as_int(_extract_number(run, "RecordsRead", "records.read", default=0.0))
        records_written = _as_int(_extract_number(run, "RecordsWritten", "records.written", default=0.0))
        errors_default = 0 if run_state == "SUCCEEDED" else 0
        records_errors = _as_int(_extract_number(run, "RecordsErrors", "records.errors", default=float(errors_default)))

        error_category = _resolve_error_category(run) if run_state == "FAILED" else None
        attrs: dict[str, Any] = {
            "aws.glue.job.name": job_name,
            "aws.glue.job.run_id": run_id,
            "aws.glue.job.type": job_type,
            "aws.glue.job.run_state": run_state,
            "aws.glue.worker.type": worker_type,
            "aws.glue.worker.count": worker_count,
            "aws.glue.dpu_seconds": dpu_seconds,
            "aws.glue.records.read": records_read,
            "aws.glue.records.written": records_written,
            "aws.glue.records.errors": records_errors,
            "aws.glue.glue_version": str(run.get("GlueVersion", "")),
            "event.dataset": "aws.glue",
            "event.provider": "glue.amazonaws.com",
        }
        if error_category:
            attrs["aws.glue.error_category"] = error_category

        with self._tracer.start_as_current_span("aws.glue.job.run", attributes=attrs) as span:
            self._emit_metrics(run=run, attrs=attrs, elapsed_time_ms=elapsed_time_ms)
            self._emit_threshold_events(span=span, run=run, attrs=attrs)
            if run_state == "FAILED" and error_category:
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute("error.code", error_category)
                self._failure_count.add(1, {"aws.glue.job.name": job_name, "aws.glue.error_category": error_category})
                self._dispatch_failed_alert(job_name=job_name, run_id=run_id, error_category=error_category, attrs=attrs)

    def _emit_metrics(self, run: dict[str, Any], attrs: dict[str, Any], elapsed_time_ms: float) -> None:
        labels = {"aws.glue.job.name": attrs["aws.glue.job.name"], "aws.glue.job.run_id": attrs["aws.glue.job.run_id"]}
        heap_used = _extract_number(run, "glue.driver.memory.heap.used_percentage", default=0.0)
        disk_used = _extract_number(run, "glue.driver.disk.used_percentage", default=0.0)
        cpu_load = _extract_number(run, "glue.driver.system.cpuSystemLoad", default=0.0)
        worker_utilization = _extract_number(run, "glue.driver.workerUtilization", default=0.0)
        skewness = _extract_number(run, "glue.driver.skewness.job", default=0.0)
        failed_tasks = _as_int(_extract_number(run, "glue.driver.aggregate.numFailedTasks", default=0.0))

        self._heap_used_pct.set(heap_used, labels)
        self._disk_used_pct.set(disk_used, labels)
        self._cpu_load.set(cpu_load, labels)
        self._worker_utilization.set(worker_utilization, labels)
        self._job_skewness.set(skewness, labels)
        self._elapsed_time_ms.record(elapsed_time_ms, labels)
        self._failed_tasks.add(failed_tasks, labels)

    def _emit_threshold_events(self, span: Any, run: dict[str, Any], attrs: dict[str, Any]) -> None:
        values = {
            "glue.driver.memory.heap.used_percentage": _extract_number(run, "glue.driver.memory.heap.used_percentage", default=0.0),
            "glue.driver.system.cpuSystemLoad": _extract_number(run, "glue.driver.system.cpuSystemLoad", default=0.0),
            "glue.driver.skewness.job": _extract_number(run, "glue.driver.skewness.job", default=0.0),
            "glue.driver.workerUtilization": _extract_number(run, "glue.driver.workerUtilization", default=0.0),
            "glue.driver.disk.used_percentage": _extract_number(run, "glue.driver.disk.used_percentage", default=0.0),
        }
        checks = (
            ("glue.driver.memory.heap.used_percentage", values["glue.driver.memory.heap.used_percentage"], self._thresholds.heap_used_pct_critical),
            ("glue.driver.system.cpuSystemLoad", values["glue.driver.system.cpuSystemLoad"], self._thresholds.cpu_load_warn),
            ("glue.driver.skewness.job", values["glue.driver.skewness.job"], self._thresholds.skewness_warn),
            ("glue.driver.workerUtilization", values["glue.driver.workerUtilization"], self._thresholds.worker_utilization_warn),
            ("glue.driver.disk.used_percentage", values["glue.driver.disk.used_percentage"], self._thresholds.disk_used_pct_warn),
        )
        for metric_name, observed, threshold in checks:
            if observed >= threshold:
                logger.warning(
                    "Glue monitor threshold exceeded metric=%s value=%s threshold=%s job=%s run_id=%s",
                    metric_name,
                    observed,
                    threshold,
                    attrs["aws.glue.job.name"],
                    attrs["aws.glue.job.run_id"],
                )
                span.add_event(
                    "glue.monitor.threshold_exceeded",
                    attributes={"metric.name": metric_name, "metric.value": observed, "metric.threshold": threshold},
                )

    def _dispatch_failed_alert(self, job_name: str, run_id: str, error_category: str, attrs: dict[str, Any]) -> None:
        if error_category in _CRITICAL_PD_CATEGORIES and self._pagerduty is not None:
            self._pagerduty.trigger(
                PagerDutyEvent(
                    summary=f"AWS Glue job failed: {job_name} ({error_category})",
                    severity="CRITICAL",
                    component="aws-glue",
                    dedup_key=run_id,
                    custom_details=attrs,
                )
            )
            return

        if self._slack is not None:
            self._slack.send(
                SlackEvent(
                    title=f"AWS Glue job failed: {job_name}",
                    text=f"run_id={run_id} category={error_category}",
                    severity="high",
                    dataset="aws.glue",
                )
            )


def _parse_jobs_from_env() -> list[str]:
    return [job.strip() for job in os.getenv("DATAOBS_GLUE_JOB_NAMES", "").split(",") if job.strip()]


async def _async_main() -> None:
    monitor = GlueJobMonitor(job_names=_parse_jobs_from_env(), poll_interval_seconds=60)
    await monitor.run_forever()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(_async_main())
