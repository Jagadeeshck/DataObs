"""Issue #25 production vertical-slice certification."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest
import requests
from elasticsearch import Elasticsearch
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.alerting.dispatcher import AlertDispatcher
from src.alerting.pagerduty import PagerDutyClient, PagerDutyConfig
from src.alerting.servicenow import ServiceNowClient, ServiceNowConfig
from src.alerting.slack import SlackClient, SlackConfig
from src.quality.checks.in_memory_null_check import InMemoryNullCheck
from src.quality.runner import QualityRunner

WEBHOOK = "http://localhost:8089"
HEADERS_A = {"X-DataObs-Tenant": "signal-tenant-a"}


def _wait_for_trace(es: Elasticsearch, execution_id: str) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        response = es.search(index="dataobs-traces", query={"match": {"attributes.dataobs.execution.id": execution_id}})
        if response["hits"]["hits"]:
            return response["hits"]["hits"][0]["_source"]
        time.sleep(0.5)
    pytest.fail(f"trace for execution {execution_id} did not reach Elasticsearch")


def _dispatcher(es: Elasticsearch, *, slack_suffix: str = "") -> AlertDispatcher:
    return AlertDispatcher(
        es,
        slack=SlackClient(SlackConfig(webhook_url=f"{WEBHOOK}/slack{slack_suffix}")),
        pagerduty=PagerDutyClient(PagerDutyConfig("integration-routing-key", events_api_url=f"{WEBHOOK}/pagerduty")),
        servicenow=ServiceNowClient(ServiceNowConfig(WEBHOOK, "integration-user", "integration-password")),
    )


@pytest.mark.integration
def test_complete_quality_signal_path(api_client: str) -> None:
    requests.delete(f"{WEBHOOK}/_requests", timeout=5)
    es = Elasticsearch("http://localhost:9200")
    resource = Resource.create({"service.name": "dataobs-quality"})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True), export_interval_millis=1000
            )
        ],
    )
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    failed = {
        "dataset": "orders",
        "table": "orders",
        "column": "customer_id",
        "check_id": "orders-nullness",
        "severity": "critical",
        "max_null_pct": 0,
        "rows": [{"customer_id": None}, {"customer_id": "42"}],
    }
    runner = QualityRunner(es, dispatcher=_dispatcher(es))
    first = runner.execute(InMemoryNullCheck(), failed, None, tenant_id="signal-tenant-a", environment="production")
    assert first.result.status == "FAIL"
    assert first.dispatch and first.dispatch.completely_successful
    assert tracer_provider.force_flush(10_000) and meter_provider.force_flush(10_000)

    api_result = requests.get(f"{api_client}/quality/results/{first.result_id}", headers=HEADERS_A, timeout=10)
    assert api_result.status_code == 200
    assert api_result.json()["execution_id"] == first.execution_id
    finding = requests.get(f"{api_client}/api/v1/findings/{first.finding['id']}", headers=HEADERS_A, timeout=10)
    assert finding.status_code == 200 and finding.json()["trace_id"] == first.trace_id
    span = _wait_for_trace(es, first.execution_id)
    assert span["trace_id"] == first.trace_id
    assert span["attributes"]["dataobs.tenant.id"] == "signal-tenant-a"
    assert span["attributes"]["dataobs.check.status"] == "FAIL"

    captured = requests.get(f"{WEBHOOK}/_requests", timeout=5).json()["requests"]
    assert {item["path"] for item in captured} == {"/slack", "/pagerduty", "/servicenow/api/now/table/incident"}
    assert all("signal-tenant-a" in json.dumps(item["body"]) for item in captured)
    assert "integration-routing-key" not in json.dumps(captured)

    second = runner.execute(InMemoryNullCheck(), failed, None, tenant_id="signal-tenant-a", environment="production")
    assert second.dispatch and second.dispatch.deduplicated and not second.dispatch.deliveries
    assert second.incident["id"] == first.incident["id"] and second.incident["occurrence_count"] == 2
    assert len(requests.get(f"{WEBHOOK}/_requests", timeout=5).json()["requests"]) == 3

    other = runner.execute(InMemoryNullCheck(), failed, None, tenant_id="signal-tenant-b", environment="production")
    assert other.incident["id"] != first.incident["id"]
    assert (
        requests.get(f"{api_client}/quality/results/{other.result_id}", headers=HEADERS_A, timeout=10).status_code
        == 404
    )
    assert (
        requests.get(f"{api_client}/api/v1/findings/{other.finding['id']}", headers=HEADERS_A, timeout=10).status_code
        == 404
    )

    before_pass = len(requests.get(f"{WEBHOOK}/_requests", timeout=5).json()["requests"])
    passing = {**failed, "check_id": "orders-nullness-pass", "rows": [{"customer_id": "42"}]}
    passed = runner.execute(InMemoryNullCheck(), passing, None, tenant_id="signal-tenant-a", environment="production")
    assert passed.result.status == "PASS" and passed.finding is None
    assert len(requests.get(f"{WEBHOOK}/_requests", timeout=5).json()["requests"]) == before_pass
    assert tracer_provider.force_flush(10_000)
    _wait_for_trace(es, passed.execution_id)

    partial_runner = QualityRunner(es, dispatcher=_dispatcher(es, slack_suffix="?status=500"))
    partial = partial_runner.execute(
        InMemoryNullCheck(),
        {**failed, "check_id": "orders-nullness-partial"},
        None,
        tenant_id="signal-tenant-a",
        environment="production",
    )
    statuses = {item.channel: item.status for item in partial.dispatch.deliveries}
    assert statuses == {"slack": "failed", "pagerduty": "succeeded", "servicenow": "succeeded"}
    assert not partial.dispatch.completely_successful

    evidence = Path("artifacts/e2e-signal-path")
    evidence.mkdir(parents=True, exist_ok=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    summary = {
        "commit_sha": sha,
        "elasticsearch_version": es.info()["version"]["number"],
        "execution_id": first.execution_id,
        "trace_id": first.trace_id,
        "tenant": "signal-tenant-a",
        "environment": "production",
        "scenarios": [
            "failed complete path",
            "persistent deduplication",
            "tenant isolation",
            "successful check",
            "partial channel failure",
        ],
        "counts": {"deliveries": 3, "incident_occurrences": 2},
        "deduplication": {
            "incident_id": first.incident["id"],
            "replayed_incident_id": second.incident["id"],
            "notification_replay_count": 0,
        },
        "status": "passed",
    }
    (evidence / "signal-path-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (evidence / "otel-correlation.json").write_text(
        json.dumps({"execution_id": first.execution_id, "trace_id": first.trace_id}, indent=2) + "\n"
    )
    (evidence / "alert-delivery-summary.json").write_text(
        json.dumps({"channels": statuses, "captured_count": len(captured), "credentials_redacted": True}, indent=2)
        + "\n"
    )
