"""Fixtures for test-owned Elasticsearch foundation evidence."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from elasticsearch import Elasticsearch

from scripts.certification.data_product_evidence import EvidenceScenarioRecorder

PROFILE = "data-product-runtime-foundation"


@pytest.fixture
def elasticsearch_client():
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("real Elasticsearch opt-in")
    client = Elasticsearch(os.environ["ELASTICSEARCH_URL"])
    version = client.info()["version"]["number"]
    assert version == "9.4.2", f"certification requires exactly Elasticsearch 9.4.2, got {version}"
    return client


@pytest.fixture
def elasticsearch_version(elasticsearch_client):
    return elasticsearch_client.info()["version"]["number"]


@pytest.fixture
def unique_scope():
    suffix = uuid4().hex
    return {"tenant": f"cert-tenant-{suffix}", "environment": f"cert-env-{suffix}", "product": suffix}


@pytest.fixture
def scenario_recorder(request):
    output = os.getenv("DATA_PRODUCT_EVIDENCE_DIR")
    profile = os.getenv("DATA_PRODUCT_CERTIFICATION_PROFILE")
    assert output, "DATA_PRODUCT_EVIDENCE_DIR is required for real certification tests"
    assert profile == PROFILE, f"explicit {PROFILE} profile is required"

    def make(filename: str, scenario: str):
        return EvidenceScenarioRecorder(Path(output), filename, scenario, profile, request.node.nodeid)

    return make
