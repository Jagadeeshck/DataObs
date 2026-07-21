"""Live Kafka, Connect, Registry, and DataObs storage certification."""

import pytest

from tests.certification.clients.connect import ConnectClient
from tests.certification.clients.kafka import KafkaClient
from tests.certification.clients.schema_registry import SchemaRegistryClient

pytestmark = pytest.mark.kafka


def test_kafka_cluster_and_dataobs_storage_are_live(live_stack):
    api, es = live_stack
    metadata = KafkaClient().admin().list_topics(timeout=10)
    assert len(metadata.brokers) == 3
    assert "certification-orders" in metadata.topics
    assert isinstance(es.request("/_cat/indices?format=json"), list)
    assert api.request("/health")["status"] in {"ok", "healthy"}


def test_connect_and_schema_registry_are_ready(live_stack):
    assert isinstance(ConnectClient().request("/connectors"), list)
    assert isinstance(SchemaRegistryClient().request("/subjects"), list)
