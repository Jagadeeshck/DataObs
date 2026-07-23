"""Executable migration and mapping foundation scenarios."""

import hashlib
import json

import pytest

from services.data_products.elasticsearch_repository import OPERATIONS, REQUIRED_RESOURCES


def _mapping(client):
    return client.indices.get_mapping(index=OPERATIONS)[OPERATIONS]["mappings"]


@pytest.mark.parametrize(
    ("filename", "scenario"),
    [
        ("migration-clean-install.json", "clean install through latest migration"),
        ("migration-upgrade.json", "released 0016 state upgraded through 0017"),
        ("migration-repeat-apply.json", "repeat migration application is stable"),
        ("mapping-contract.json", "operation-state mapping writer parity"),
    ],
)
def test_foundation_migration_and_mapping_scenarios(
    elasticsearch_client, elasticsearch_version, scenario_recorder, filename, scenario
):
    recorder = scenario_recorder(filename, scenario)
    existing = {name for name in REQUIRED_RESOURCES if elasticsearch_client.indices.exists(index=name)}
    recorder.assert_that(existing == set(REQUIRED_RESOURCES), "all required Data Product indices exist")
    mapping = _mapping(elasticsearch_client)
    properties = mapping["properties"]
    recorder.assert_that(properties["tenant_id"]["type"] == "keyword", "tenant scope is mapped as keyword")
    recorder.assert_that(properties["next_attempt_at"]["type"] == "date", "0017 next_attempt_at is mapped as date")
    recorder.assert_that(properties["document"]["type"] == "flattened", "operation payload remains flattened")
    checksum = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    recorder.reference(checksum)
    recorder.passed(elasticsearch_version)
