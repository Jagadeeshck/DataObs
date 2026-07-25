import json
import os
from pathlib import Path

import pytest
from elasticsearch import Elasticsearch

from packages.elastic_store.manifest import BASE_PROPERTIES, MIGRATION_STATE_INDEX, migrations
from packages.elastic_store.registry import apply, status
from services.incident_manager.elasticsearch_repository import ElasticsearchIncidentRepository
from services.incident_manager.service import IncidentManagerService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="requires isolated Elasticsearch 9.4.2"
)


@pytest.fixture()
def es():
    client = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
    client.options(ignore_status=[404]).indices.delete(index="dataobs-*", expand_wildcards="all")
    yield client
    client.options(ignore_status=[404]).indices.delete(index="dataobs-*", expand_wildcards="all")


def _historical_0011(es):
    old = {"dynamic": "strict", "properties": BASE_PROPERTIES | {"id": {"type": "keyword"}}}
    for index in ("dataobs-findings-v1", "dataobs-incidents-v1"):
        es.indices.create(index=index, mappings=old)
        es.indices.put_alias(index=index, name=f"{index}-read")
        es.indices.put_alias(index=index, name=f"{index}-write", is_write_index=True)
    es.indices.create(
        index=MIGRATION_STATE_INDEX,
        mappings={
            "dynamic": "strict",
            "properties": {
                "migration_id": {"type": "keyword"},
                "schema_version": {"type": "keyword"},
                "checksum": {"type": "keyword"},
                "applied_at": {"type": "date"},
                "status": {"type": "keyword"},
            },
        },
    )
    for migration in migrations()[:11]:
        es.index(
            index=MIGRATION_STATE_INDEX,
            id=migration.migration_id,
            document={
                "migration_id": migration.migration_id,
                "schema_version": migration.schema_version,
                "checksum": migration.checksum,
                "applied_at": "2026-07-21T00:00:00Z",
                "status": "applied",
            },
            refresh="wait_for",
        )


def test_upgrade_existing_0011_indices_and_rerun(es):
    _historical_0011(es)
    es.index(
        index="dataobs-incidents-v1",
        id="old",
        document={"id": "old", "tenant_id": "t1", "environment": "prod"},
        refresh="wait_for",
    )
    apply(es)
    assert status(es)["ready"] is True
    assert es.get(index="dataobs-incidents-v1", id="old")["_source"]["id"] == "old"
    mapping = es.indices.get_mapping(index="dataobs-incidents-v1")["dataobs-incidents-v1"]["mappings"]
    assert mapping["dynamic"] == "strict"
    assert mapping["properties"]["occurrence_count"]["type"] == "long"
    before = es.get(index=MIGRATION_STATE_INDEX, id="0012_incident_mapping_and_occ_fix")["_source"]
    apply(es)
    assert es.get(index=MIGRATION_STATE_INDEX, id="0012_incident_mapping_and_occ_fix")["_source"] == before


def test_incompatible_mapping_fails_without_recording_0012(es):
    _historical_0011(es)
    es.indices.delete(index="dataobs-incidents-v1")
    es.indices.create(
        index="dataobs-incidents-v1",
        mappings={"dynamic": "strict", "properties": {"occurrence_count": {"type": "keyword"}}},
    )
    with pytest.raises(RuntimeError, match="Incompatible existing mapping"):
        apply(es)
    assert (
        es.options(ignore_status=[404])
        .get(index=MIGRATION_STATE_INDEX, id="0012_incident_mapping_and_occ_fix")
        .meta.status
        == 404
    )


def test_replay_sequence_and_occurrence_evidence(es):
    apply(es)
    service = IncidentManagerService(ElasticsearchIncidentRepository(es))
    base = {
        "id": "event-1",
        "tenant_id": "t1",
        "environment": "prod",
        "asset_id": "asset-1",
        "event_type": "schema_change",
        "observed_at": "2026-07-21T10:00:00Z",
        "evidence": [{"reference": "first"}],
    }
    first = service.ingest(base, tenant_id="t1")
    exact = service.ingest(base, tenant_id="t1")
    newer = service.ingest(
        base | {"observed_at": "2026-07-21T10:01:00Z", "evidence": [{"reference": "corrected"}]},
        tenant_id="t1",
    )
    assert exact["incident"]["seq_no"] == first["incident"]["seq_no"]
    assert newer["incident"]["seq_no"] == first["incident"]["seq_no"] + 1
    assert newer["incident"]["occurrence_count"] == 1
    assert exact["ingestion"]["reason"] == "exact_replay"
    evidence = {
        "first_seq_no": first["incident"]["seq_no"],
        "exact_replay_seq_no": exact["incident"]["seq_no"],
        "corrected_replay_seq_no": newer["incident"]["seq_no"],
    }
    Path("replay-sequence-number-evidence.json").write_text(json.dumps(evidence, indent=2))
