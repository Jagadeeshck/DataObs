"""Real persistence-security certification fixtures."""

import os
from pathlib import Path

import pytest
from elasticsearch import Elasticsearch


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
