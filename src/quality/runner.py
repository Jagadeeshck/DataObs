"""Reusable, one-shot execution path for production quality checks."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from elasticsearch import Elasticsearch
from opentelemetry import metrics, trace

from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository
from services.incident_manager.service import IncidentManagerService
from src.alerting.dispatcher import AlertDispatcher, DispatchResult
from src.api.es_store import ElasticsearchStore
from src.quality.checks.base import BaseCheck, CheckResult


@dataclass(frozen=True)
class QualityExecution:
    result: CheckResult
    result_id: str
    execution_id: str
    trace_id: str
    finding: dict[str, Any] | None
    incident: dict[str, Any] | None
    dispatch: DispatchResult | None


class QualityRunner:
    """Execute, correlate, persist, instrument, and orchestrate one check."""

    def __init__(self, es_client: Elasticsearch, *, dispatcher: AlertDispatcher | None = None) -> None:
        self.es = es_client
        self.dispatcher = dispatcher

    def execute(
        self,
        check: BaseCheck,
        config: dict[str, Any],
        connection: Any,
        *,
        tenant_id: str,
        environment: str,
        execution_id: str | None = None,
    ) -> QualityExecution:
        execution_id = execution_id or str(uuid.uuid4())
        dataset = str(config["dataset"])
        attributes: dict[str, str] = {
            "dataobs.tenant.id": tenant_id,
            "dataobs.environment": environment,
            "dataobs.execution.id": execution_id,
            "dataobs.dataset": dataset,
            "dataobs.check.type": check.check_type,
            "dataobs.check.severity": str(config.get("severity", "high")),
        }
        for name in ("table", "column"):
            if config.get(name):
                attributes[f"dataobs.{name}"] = str(config[name])
        tracer = trace.get_tracer("dataobs.quality.runner")
        with tracer.start_as_current_span("dataobs.quality.check", attributes=attributes) as span:
            result = check.run(config, connection)
            span.set_attribute("dataobs.check.status", result.status)
            span.set_attribute("dataobs.check.severity", result.severity)
            trace_id = format(span.get_span_context().trace_id, "032x")
            result_id = hashlib.sha256(f"{tenant_id}:{execution_id}".encode()).hexdigest()
            document = {
                **result.to_es_doc(),
                "id": result_id,
                "execution_id": execution_id,
                "check_id": str(config.get("check_id") or config.get("check_name") or check.check_type),
                "check_name": str(config.get("check_name") or check.check_type),
                "environment": environment,
                "table": config.get("table"),
                "column": config.get("column"),
                "otel_trace_id": trace_id,
            }
            ElasticsearchStore(self.es, tenant_id=tenant_id).save_quality_result(document)
            metrics.get_meter("dataobs.quality.runner").create_counter("dataobs.quality.checks_run").add(1, attributes)
            finding = incident = None
            dispatch = None
            if result.status == "FAIL":
                orchestration = IncidentManagerService(ElasticsearchIncidentRepository(self.es)).ingest(
                    {
                        **document,
                        "event_type": "quality_result",
                        "tenant_id": tenant_id,
                        "asset_id": dataset,
                        "environment": environment,
                        "correlation_id": execution_id,
                        "trace_id": trace_id,
                        "monitor_id": document["check_id"],
                    },
                    tenant_id=tenant_id,
                )
                finding, incident = orchestration["finding"], orchestration["incident"]
                if self.dispatcher:
                    dispatch = self.dispatcher.dispatch(
                        finding,
                        incident,
                        is_new=orchestration["ingestion"]["status"] == "created",
                    )
            return QualityExecution(result, result_id, execution_id, trace_id, finding, incident, dispatch)
