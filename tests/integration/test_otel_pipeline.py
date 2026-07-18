"""OTLP HTTP to collector to Elasticsearch integration coverage."""

from __future__ import annotations

import time

import pytest
import requests


@pytest.mark.integration
def test_otel_span_reaches_elasticsearch(es_client: str) -> None:
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "dataobs-quality-worker"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "0af7651916cd43dd8448eb211c80319c",
                                "spanId": "b7ad6b7169203331",
                                "name": "quality.failure",
                                "kind": 1,
                                "startTimeUnixNano": "1710000000000000000",
                                "endTimeUnixNano": "1710000001000000000",
                                "attributes": [
                                    {"key": "db.system.name", "value": {"stringValue": "postgresql"}},
                                    {"key": "db.namespace", "value": {"stringValue": "warehouse"}},
                                    {"key": "dataobs.table", "value": {"stringValue": "orders"}},
                                    {"key": "dataobs.column", "value": {"stringValue": "customer_id"}},
                                    {"key": "dataobs.check.method", "value": {"stringValue": "null_rate_drift"}},
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }
    resp = requests.post("http://localhost:4318/v1/traces", json=payload, timeout=10)
    assert resp.status_code in (200, 202), resp.text

    query = {"query": {"match": {"name": "quality.failure"}}}
    for _ in range(30):
        found = requests.post(f"{es_client}/dataobs-traces/_search", json=query, timeout=10).json()
        hits = found.get("hits", {}).get("hits", [])
        if hits:
            source = hits[0]["_source"]
            assert "quality.failure" in str(source)
            assert "db.system.name" in str(source)
            assert "dataobs.check.method" in str(source)
            return
        time.sleep(1)
    pytest.fail("OTel span was not indexed into Elasticsearch dataobs-traces")
