"""Real persistence-security certification fixtures."""

import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from elasticsearch import Elasticsearch


@dataclass(frozen=True)
class ExecutedSecurityControl:
    control_id: str
    test_node_id: str
    assertion_count: int
    passed: bool
    redacted_references: tuple[str, ...] = ()


@pytest.fixture
def executed_control(request):
    def record(control_id: str, assertion_count: int) -> ExecutedSecurityControl:
        assert assertion_count > 0
        return ExecutedSecurityControl(control_id, request.node.nodeid, assertion_count, True)

    return record


@pytest.fixture
def security_client():
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("real Elasticsearch security opt-in")
    assert os.getenv("DATA_PRODUCT_CERTIFICATION_PROFILE") == "data-product-runtime-foundation"
    assert os.getenv("DATA_PRODUCT_EVIDENCE_DIR")
    client = Elasticsearch(os.environ["ELASTICSEARCH_URL"])
    assert client.info()["version"]["number"] == "9.4.2"
    return client


@pytest.fixture
def security_evidence_dir():
    return Path(os.environ["DATA_PRODUCT_EVIDENCE_DIR"])
