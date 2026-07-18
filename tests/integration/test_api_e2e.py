"""
End-to-end API tests: POST quality result → GET by ID → assert stored.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/25
"""

from __future__ import annotations

import pytest
import requests


@pytest.mark.integration
def test_quality_result_round_trip(api_client: str) -> None:
    """POST a quality result and retrieve it by ID."""
    payload = {
        "check_name": "null_check",
        "table": "orders",
        "column": "customer_id",
        "status": "failed",
        "score": 0.12,
        "tenant_id": "test-tenant",
    }
    post_resp = requests.post(f"{api_client}/quality/results", json=payload, timeout=10)
    assert post_resp.status_code == 201, post_resp.text
    result_id = post_resp.json()["id"]

    get_resp = requests.get(f"{api_client}/quality/results/{result_id}", timeout=10)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["check_name"] == "null_check"
    assert data["status"] == "failed"
    assert data["id"] == result_id


@pytest.mark.integration
def test_rule_crud(api_client: str) -> None:
    """POST a rule, list rules, assert it appears."""
    rule = {
        "check_type": "null_check",
        "table": "events",
        "column": "event_type",
        "config": {"threshold": 0.05},
    }
    post_resp = requests.post(f"{api_client}/rules", json=rule, timeout=10)
    assert post_resp.status_code in (200, 201), post_resp.text
    rule_id = post_resp.json().get("rule_id") or post_resp.json().get("id")

    list_resp = requests.get(f"{api_client}/rules", timeout=10)
    assert list_resp.status_code == 200
    ids = [r.get("rule_id") or r.get("id") for r in list_resp.json()]
    assert rule_id in ids
