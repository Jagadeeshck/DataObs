"""Destructive, test-only proof of the released migration paths."""

import hashlib
import json
import os
from urllib.parse import urlparse

from packages.elastic_store.manifest import MIGRATION_STATE_INDEX, migrations, registered_mutable_resources
from packages.elastic_store.registry import apply, status
from services.data_products.elasticsearch_repository import OPERATIONS, REQUIRED_RESOURCES


def _reset(client) -> None:
    """Delete only registered resources on the dedicated loopback service."""
    endpoint = urlparse(os.environ.get("ELASTICSEARCH_URL", ""))
    if (
        os.getenv("RUN_INTEGRATION_TESTS") != "1"
        or os.getenv("DATA_PRODUCT_ALLOW_DESTRUCTIVE_TEST_RESET") != "1"
        or endpoint.hostname not in {"127.0.0.1", "localhost"}
        or endpoint.port != 9200
    ):
        raise RuntimeError("destructive certification reset is not explicitly authorized")
    resources = set(registered_mutable_resources())
    if any("*" in resource or "?" in resource for resource in resources):
        raise RuntimeError("wildcards are forbidden in the destructive resource registry")
    for resource in sorted(resources):
        if client.indices.exists(index=resource):
            client.indices.delete(index=resource)


def _mapping(client):
    return client.indices.get_mapping(index=OPERATIONS)[OPERATIONS]["mappings"]


def test_clean_install_executes_all_released_migrations(elasticsearch_client, elasticsearch_version, scenario_recorder):
    _reset(elasticsearch_client)
    assert not elasticsearch_client.indices.exists(index=MIGRATION_STATE_INDEX)
    assert not any(elasticsearch_client.indices.exists(index=name) for name in REQUIRED_RESOURCES)
    applied = apply(elasticsearch_client)
    migration_status = status(elasticsearch_client)
    expected = migrations()
    assert len(applied) == len(expected)
    assert migration_status["ready"]
    assert set(migration_status["applied"]) == {item.migration_id for item in expected}
    assert all(migration_status["applied"][item.migration_id]["checksum"] == item.checksum for item in expected)
    assert all(elasticsearch_client.indices.exists(index=name) for name in REQUIRED_RESOURCES)
    recorder = scenario_recorder("migration-clean-install.json", "clean install through latest migration")
    recorder.assert_that(True, "cluster began clean and registry apply executed")
    recorder.assert_that(len(applied) == len(expected), "exact released migration count observed")
    recorder.reference(expected[-1].migration_id)
    recorder.passed(elasticsearch_version)


def test_upgrade_from_0016_executes_0017_once(elasticsearch_client, elasticsearch_version, scenario_recorder):
    _reset(elasticsearch_client)
    through = "0016_data_product_membership_dependency_runtime"
    before = apply(elasticsearch_client, through_migration_id=through)
    assert before[-1]["migration_id"] == through
    assert "next_attempt_at" not in _mapping(elasticsearch_client)["properties"]
    legacy_id = "legacy-operation-before-0017"
    elasticsearch_client.index(
        index=OPERATIONS,
        id=legacy_id,
        document={
            "tenant_id": "legacy",
            "environment": "test",
            "operation_id": legacy_id,
            "product_id": "product",
            "action": "manual_membership",
            "outcome": "pending",
            "occurred_at": "2026-01-01T00:00:00Z",
            "document": {"status": "pending"},
        },
        refresh="wait_for",
    )
    prior = status(elasticsearch_client)["applied"].copy()
    apply(elasticsearch_client)
    after = status(elasticsearch_client)
    latest = migrations()[-1]
    assert after["applied"][latest.migration_id]["checksum"] == latest.checksum
    assert _mapping(elasticsearch_client)["properties"]["next_attempt_at"]["type"] == "date"
    assert elasticsearch_client.get(index=OPERATIONS, id=legacy_id)["found"]
    assert all(after["applied"][key] == value for key, value in prior.items())
    recorder = scenario_recorder("migration-upgrade.json", "released 0016 state upgraded through 0017")
    recorder.assert_that(True, "0016 prefix applied and 0017 was initially absent")
    recorder.assert_that(True, "0017 applied once without changing legacy evidence")
    recorder.reference(latest.checksum)
    recorder.passed(elasticsearch_version)


def test_repeat_apply_is_idempotent(elasticsearch_client, elasticsearch_version, scenario_recorder):
    apply(elasticsearch_client)
    before = status(elasticsearch_client)["applied"]
    mapping_checksum = hashlib.sha256(json.dumps(_mapping(elasticsearch_client), sort_keys=True).encode()).hexdigest()
    first, second = apply(elasticsearch_client), apply(elasticsearch_client)
    assert len(first) == len(second) == len(migrations())
    assert status(elasticsearch_client)["applied"] == before
    assert (
        hashlib.sha256(json.dumps(_mapping(elasticsearch_client), sort_keys=True).encode()).hexdigest()
        == mapping_checksum
    )
    recorder = scenario_recorder("migration-repeat-apply.json", "repeat migration application is stable")
    recorder.assert_that(True, "two full apply calls completed without duplicate records")
    recorder.reference(mapping_checksum)
    recorder.passed(elasticsearch_version)


def test_mapping_contract_uses_installed_mapping(elasticsearch_client, elasticsearch_version, scenario_recorder):
    mapping = _mapping(elasticsearch_client)
    properties = mapping["properties"]
    for field, kind in {
        "tenant_id": "keyword",
        "environment": "keyword",
        "product_id": "keyword",
        "operation_id": "keyword",
        "action": "keyword",
        "outcome": "keyword",
        "occurred_at": "date",
        "next_attempt_at": "date",
        "document": "flattened",
    }.items():
        assert properties[field]["type"] == kind
    checksum = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    recorder = scenario_recorder("mapping-contract.json", "installed operation-state mapping contract")
    recorder.assert_that(mapping["dynamic"] == "strict", "mapping rejects unknown top-level fields")
    recorder.reference(checksum)
    recorder.passed(elasticsearch_version)
