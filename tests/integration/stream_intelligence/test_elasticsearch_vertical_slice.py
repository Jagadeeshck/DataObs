"""Opt-in Elasticsearch 9.4.2 mapping contract for Stream Intelligence."""

import os

import pytest
from elasticsearch import Elasticsearch

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_STREAM_INTELLIGENCE_ELASTICSEARCH_TESTS") != "1", reason="requires Elasticsearch 9.4.2"
)
def test_intelligence_resources_are_strict_and_scoped():
    es = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
    assert es.info()["version"]["number"] == "9.4.2"
    for index in (
        "dataobs-stream-detector-definitions-v1",
        "dataobs-stream-anomaly-current-v1",
        "dataobs-stream-retention-forecast-current-v1",
        "dataobs-stream-failure-candidate-current-v1",
        "dataobs-stream-intelligence-runtime-state-v1",
    ):
        mapping = es.indices.get_mapping(index=index)[index]["mappings"]
        assert mapping["dynamic"] == "strict"
        assert {"tenant_id", "environment", "resource_type", "resource_id", "schema_version"} <= mapping[
            "properties"
        ].keys()
