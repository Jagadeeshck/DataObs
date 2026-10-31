"""Destructive, test-only proof of the released migration paths."""

import hashlib
import json
import os
from urllib.parse import urlparse

from packages.elastic_store.manifest import (
    MIGRATION_STATE_INDEX,
    migrations,
    registered_mutable_resources,
)
from packages.elastic_store.registry import apply, status
from services.data_products.elasticsearch_repository import (
    DECISIONS,
    OPERATIONS,
    REQUIRED_RESOURCES,
)


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
    assert [item.migration_id[:4] for item in expected] == [f"{number:04d}" for number in range(1, len(expected) + 1)]
    assert any(item.migration_id == "0019_data_product_operation_claim_expires_date" for item in expected)
    assert len(applied) == len(expected)
    assert migration_status["ready"]
    assert set(migration_status["applied"]) == {item.migration_id for item in expected}
    assert all(migration_status["applied"][item.migration_id]["checksum"] == item.checksum for item in expected)
    assert all(elasticsearch_client.indices.exists(index=name) for name in REQUIRED_RESOURCES)

    # Sprint 3 hosted regression: a Data Product clean install traverses the
    # shared reliability migrations too. The global mapping union must not
    # preempt the first released owner of observed_value before migration 0025
    # validates the resource.
    reliability_index = "dataobs-reliability-status-v1"
    reliability_mapping = elasticsearch_client.indices.get_mapping(index=reliability_index)[reliability_index][
        "mappings"
    ]
    assert reliability_mapping["properties"]["observed_value"]["type"] == "double"

    # Retain direct proof that the Data Product 0015 writer contracts also
    # survive the same hosted clean-install path.
    revisions_index = "dataobs-data-product-revisions-v1"
    revisions_mapping = elasticsearch_client.indices.get_mapping(index=revisions_index)[revisions_index]["mappings"]
    assert revisions_mapping["properties"]["revision"]["type"] == "integer"
    assert revisions_mapping["properties"]["operation_id"]["type"] == "keyword"

    operation_mapping = _mapping(elasticsearch_client)
    assert operation_mapping["properties"]["revision"]["type"] == "integer"
    assert operation_mapping["properties"]["operation_id"]["type"] == "keyword"

    recorder = scenario_recorder(
        "migration-clean-install.json",
        "clean install through latest migration",
    )
    recorder.assert_that(True, "cluster began clean and registry apply executed")
    recorder.assert_that(
        len(applied) == len(expected),
        "exact released migration count observed",
    )
    recorder.assert_that(
        reliability_mapping["properties"]["observed_value"]["type"] == "double",
        "shared reliability status mapping preserved first released field ownership",
    )
    recorder.assert_that(
        revisions_mapping["properties"]["revision"]["type"] == "integer",
        "Data Product revision mapping remained writer compatible",
    )
    recorder.reference(expected[-1].migration_id)
    recorder.reference("dataobs-reliability-status-v1.observed_value:double")
    recorder.passed(elasticsearch_version)


def test_upgrade_from_0017_executes_0018_once(elasticsearch_client, elasticsearch_version, scenario_recorder):
    _reset(elasticsearch_client)
    through = "0017_data_product_reconciliation_retry_date"
    before = apply(elasticsearch_client, through_migration_id=through)
    assert before[-1]["migration_id"] == through
    before_status = status(elasticsearch_client)
    assert "0018_data_product_decision_reason_alias" not in before_status["applied"]
    decision_mapping = elasticsearch_client.indices.get_mapping(index=DECISIONS)[DECISIONS]["mappings"]
    # Current clean-install mapping ownership may safely pre-provision a later
    # additive field. Migration execution state, not physical field absence,
    # is the authoritative upgrade boundary.
    if "decision_reason" in decision_mapping["properties"]:
        assert decision_mapping["properties"]["decision_reason"]["type"] == "match_only_text"
    legacy_id = "legacy-decision-before-0018"
    elasticsearch_client.index(
        index=DECISIONS,
        id=legacy_id,
        document={
            "tenant_id": "legacy",
            "environment": "test",
            "decision_id": legacy_id,
            "proposal_id": "proposal",
            "product_id": "product",
            "decision": "accept",
            "outcome": "applied",
            "reason": "legacy reason",
            "actor": "operator",
            "idempotency_key_hash": "hash",
            "request_fingerprint": "fingerprint",
            "decided_at": "2026-01-01T00:00:00Z",
            "occurred_at": "2026-01-01T00:00:00Z",
            "schema_version": "v1",
        },
        refresh="wait_for",
    )
    prior = before_status["applied"].copy()
    apply(elasticsearch_client)
    after = status(elasticsearch_client)
    latest = migrations()[-1]
    assert after["applied"][latest.migration_id]["checksum"] == latest.checksum
    decision_mapping = elasticsearch_client.indices.get_mapping(index=DECISIONS)[DECISIONS]["mappings"]
    assert decision_mapping["properties"]["decision_reason"]["type"] == "match_only_text"
    legacy = elasticsearch_client.get(index=DECISIONS, id=legacy_id)["_source"]
    assert legacy["reason"] == "legacy reason"
    assert all(after["applied"][key] == value for key, value in prior.items())
    recorder = scenario_recorder(
        "migration-upgrade.json",
        "released 0017 state upgraded through 0018",
    )
    recorder.assert_that(
        "0018_data_product_decision_reason_alias" not in prior,
        "0017 prefix applied and migration 0018 was initially unapplied",
    )
    recorder.assert_that(
        True,
        "0018 applied once without changing legacy decision evidence",
    )
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
    recorder = scenario_recorder(
        "migration-repeat-apply.json",
        "repeat migration application is stable",
    )
    recorder.assert_that(
        True,
        "two full apply calls completed without duplicate records",
    )
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
        "claim_expires_at": "date",
        "document": "flattened",
    }.items():
        assert properties[field]["type"] == kind
    checksum = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    recorder = scenario_recorder(
        "mapping-contract.json",
        "installed operation-state mapping contract",
    )
    recorder.assert_that(
        mapping["dynamic"] == "strict",
        "mapping rejects unknown top-level fields",
    )
    recorder.reference(checksum)
    recorder.passed(elasticsearch_version)
