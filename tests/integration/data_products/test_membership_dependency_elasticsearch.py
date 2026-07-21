"""Focused real-Elasticsearch contract (enabled by the integration harness)."""

import os

import pytest
from elasticsearch import Elasticsearch

from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_elasticsearch_membership_dependency_profile_is_selected():
    client = Elasticsearch(os.environ["ELASTICSEARCH_URL"])
    repository = ElasticsearchDataProductRepository(client)
    assert client.info()["version"]["number"].startswith("9.4.2")
    readiness = repository.readiness()
    assert readiness["ready"], readiness
