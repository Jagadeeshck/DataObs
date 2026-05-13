"""
Unit tests for the POC observability writer.

These tests stub out Elasticsearch so they can run offline. They verify:
  - the writer issues index() calls with the expected document shape,
  - failing checks generate alert documents into dataobs-alerts,
  - the schema hash is deterministic and order-independent.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.poc.observability_writer import ObservabilityWriter, _hash_schema


@pytest.fixture
def writer_and_calls():
    calls: List[Dict[str, Any]] = []
    fake_es = MagicMock()
    fake_es.index.side_effect = lambda index, document: calls.append(
        {"index": index, "doc": document}
    )
    with patch("src.poc.observability_writer.Elasticsearch", return_value=fake_es):
        ow = ObservabilityWriter(host="http://x:9200", password="p")
    return ow, calls


def _indices(calls: List[Dict[str, Any]]) -> List[str]:
    return [c["index"] for c in calls]


def test_register_asset_writes_to_assets_index(writer_and_calls):
    ow, calls = writer_and_calls
    ow.register_asset(
        asset_id="a", name="a", asset_type="elasticsearch_index",
        platform="elasticsearch", location="x",
    )
    assert _indices(calls) == ["dataobs-assets"]
    doc = calls[0]["doc"]
    assert doc["asset.id"] == "a"
    assert doc["asset.name"] == "a"
    assert doc["tenant"] == "poc"
    assert doc["ecs.version"]
    assert doc["event.dataset"] == "dataobs.assets"
    assert doc["data_stream.dataset"] == "dataobs.assets"
    assert doc["data_stream.namespace"] == "poc"
    assert doc["service.name"] == "dataobs-poc-pipeline"
    assert doc["deployment.environment.name"] == "poc"


def test_failing_quality_check_emits_alert(writer_and_calls):
    ow, calls = writer_and_calls
    ow.emit_quality_check(
        run_id="r1", asset_id="a", asset_name="a",
        check_name="row_count_min", check_type="volume", column=None,
        value=0.0, threshold=10.0, status="fail", severity="critical",
        message="too few rows",
    )
    assert "dataobs-quality" in _indices(calls)
    assert "dataobs-alerts" in _indices(calls)
    alert = next(c["doc"] for c in calls if c["index"] == "dataobs-alerts")
    assert alert["alert.severity"] == "critical"
    assert alert["alert.source"] == "quality"
    assert alert["event.dataset"] == "dataobs.alerts"
    assert alert["event.outcome"] == "failure"


def test_passing_quality_check_no_alert(writer_and_calls):
    ow, calls = writer_and_calls
    ow.emit_quality_check(
        run_id="r1", asset_id="a", asset_name="a",
        check_name="row_count_min", check_type="volume", column=None,
        value=100.0, threshold=10.0, status="pass",
    )
    assert _indices(calls) == ["dataobs-quality"]


def test_freshness_breach_alerts(writer_and_calls):
    ow, calls = writer_and_calls
    ow.emit_freshness(
        asset_id="a", asset_name="a", last_seen="2026-05-08T00:00:00Z",
        lag_seconds=4000, sla_seconds=3600,
    )
    indices = _indices(calls)
    assert "dataobs-freshness" in indices
    assert "dataobs-alerts" in indices
    fresh = next(c["doc"] for c in calls if c["index"] == "dataobs-freshness")
    assert fresh["freshness.status"] == "stale"


def test_volume_anomaly_alerts(writer_and_calls):
    ow, calls = writer_and_calls
    ow.emit_volume(
        asset_id="a", asset_name="a", row_count=5,
        expected_min=10, expected_max=100,
    )
    assert "dataobs-alerts" in _indices(calls)
    vol = next(c["doc"] for c in calls if c["index"] == "dataobs-volume")
    assert vol["volume.status"] == "anomaly"


def test_schema_drift_detected(writer_and_calls):
    ow, calls = writer_and_calls
    ow.snapshot_schema(
        asset_id="a", asset_name="a",
        columns=[{"name": "x", "type": "long"}],
        previous_hash="aaa",
    )
    schema_doc = next(c["doc"] for c in calls if c["index"] == "dataobs-schema")
    assert schema_doc["schema.drift_event"] == "drift_detected"
    assert "dataobs-alerts" in _indices(calls)


def test_lineage_writes_full_doc(writer_and_calls):
    ow, calls = writer_and_calls
    ow.emit_lineage(
        run_id="r1", source="src", target="tgt",
        relation="transformation", row_count=42,
        fields=[{"source": "a", "target": "a"}],
    )
    assert _indices(calls) == ["dataobs-lineage"]
    doc = calls[0]["doc"]
    assert doc["source"] == "src"
    assert doc["target"] == "tgt"
    assert doc["lineage.source"] == "src"
    assert doc["lineage.target"] == "tgt"
    assert doc["event.dataset"] == "dataobs.lineage"
    assert doc["row_count"] == 42


def test_schema_hash_is_order_independent():
    h1 = _hash_schema([{"name": "a", "type": "long"}, {"name": "b", "type": "keyword"}])
    h2 = _hash_schema([{"name": "b", "type": "keyword"}, {"name": "a", "type": "long"}])
    assert h1 == h2


def test_poc_templates_include_ecs_and_otel_common_fields():
    template_path = Path("config/elasticsearch/poc-templates.json")
    data = json.loads(template_path.read_text())
    required = {
        "ecs.version",
        "data_stream.type",
        "data_stream.dataset",
        "data_stream.namespace",
        "event.kind",
        "event.category",
        "event.type",
        "event.dataset",
        "event.module",
        "event.provider",
        "event.action",
        "event.outcome",
        "service.name",
        "service.namespace",
        "service.type",
        "deployment.environment.name",
        "telemetry.sdk.language",
        "telemetry.distro.name",
        "observer.type",
        "labels.tenant",
    }
    custom_templates = {
        "dataobs-assets",
        "dataobs-quality",
        "dataobs-freshness",
        "dataobs-volume",
        "dataobs-schema",
        "dataobs-lineage",
        "dataobs-alerts",
    }
    by_name = {tpl["name"]: tpl for tpl in data["templates"]}

    for name in custom_templates:
        props = by_name[name]["body"]["template"]["mappings"]["properties"]
        assert required <= set(props), name

    lineage_props = by_name["dataobs-lineage"]["body"]["template"]["mappings"]["properties"]
    assert {"lineage.source", "lineage.target"} <= set(lineage_props)
