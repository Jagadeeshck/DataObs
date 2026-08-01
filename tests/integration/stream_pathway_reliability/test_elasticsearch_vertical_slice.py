"""Opt-in Elasticsearch 9.4.2 migration contract test.

The full API/worker transition scenario is deliberately a hosted acceptance gate; this
fixture never substitutes an in-memory store for Elasticsearch.
"""

import os

import pytest
from elasticsearch import Elasticsearch

from packages.elastic_store.registry import apply, status

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RELIABILITY_ELASTICSEARCH_TESTS") != "1",
    reason="requires RUN_RELIABILITY_ELASTICSEARCH_TESTS=1 and Elasticsearch 9.4.2",
)


def test_reliability_storage_contracts_on_real_elasticsearch():
    es = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
    assert es.info()["version"]["number"] == "9.4.2"
    apply(es)
    assert status(es)["ready"] is True
    for index in (
        "dataobs-stream-slo-definitions-v1",
        "dataobs-reliability-status-v1",
        "dataobs-reliability-runtime-state-v1",
    ):
        mapping = es.indices.get_mapping(index=index)[index]["mappings"]
        assert mapping["dynamic"] == "strict"
    templates = es.indices.get_index_template(name="dataobs-*-evaluation-*-template")["index_templates"]
    assert templates
    policies = es.ilm.get_lifecycle(name="dataobs-*")
    assert any(name.endswith("90d") for name in policies)
    assert any(name.endswith("365d") for name in policies)
