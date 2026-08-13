from dataclasses import replace

import pytest

from packages.elastic_store.manifest import (
    SCHEMA_INTELLIGENCE_PROPERTIES,
    TEAM1_STREAM_SCHEMA_INTELLIGENCE_RUNTIME_MIGRATION,
    migrations,
)
from scripts.release import current_terminal_migration


def test_team1_schema_runtime_migration_is_registered_once_and_terminal():
    registry = migrations()
    assert registry.count(TEAM1_STREAM_SCHEMA_INTELLIGENCE_RUNTIME_MIGRATION) == 1
    assert registry[-2].migration_id == "0032_team2_data_slo_production_runtime"
    assert registry[-1].migration_id == "0033_team1_stream_schema_intelligence_runtime"
    assert registry[-1].dependencies == [registry[-2].migration_id]


def test_executable_registry_is_a_unique_linear_numeric_sequence():
    registry = migrations()
    prefixes = [migration.migration_id.split("_", 1)[0] for migration in registry]
    assert len(prefixes) == len(set(prefixes))
    for previous, migration in zip(registry, registry[1:]):
        assert migration.dependencies == [previous.migration_id]


def test_terminal_helper_rejects_parallel_numeric_collisions(monkeypatch):
    registry = migrations()
    collision = replace(registry[-1], migration_id="0032_team1_collision")
    monkeypatch.setattr(current_terminal_migration, "migrations", lambda: [*registry[:-1], collision])
    with pytest.raises(ValueError, match="duplicate numeric prefixes: 0032"):
        current_terminal_migration.migration_report()


def test_schema_runtime_storage_contract_is_strict_and_privacy_safe():
    migration = TEAM1_STREAM_SCHEMA_INTELLIGENCE_RUNTIME_MIGRATION
    expected_indices = {
        "dataobs-stream-schema-subject-current-v1",
        "dataobs-stream-schema-version-current-v1",
        "dataobs-stream-schema-binding-current-v1",
        "dataobs-stream-schema-impact-current-v1",
        "dataobs-stream-schema-runtime-state-v1",
    }
    expected_streams = {
        "logs-dataobs.stream-schema-version-*",
        "logs-dataobs.stream-schema-change-*",
        "logs-dataobs.stream-schema-compatibility-*",
        "logs-dataobs.stream-schema-consumer-impact-*",
    }
    assert set(migration.operations["mutable_indices"]) == expected_indices
    assert set(migration.operations["data_stream_contracts"]) == expected_streams
    assert all(mapping["dynamic"] == "strict" for mapping in migration.operations["mapping_updates"].values())
    properties = set(SCHEMA_INTELLIGENCE_PROPERTIES["properties"])
    required = {
        "tenant_id", "environment", "integration_id", "registry_id", "subject_id", "resource_id",
        "schema_version", "schema_type", "schema_fingerprint", "compatibility_mode", "compatibility_result",
        "evaluation_method", "binding_method", "binding_confidence", "consumer_id",
        "consumer_group_or_subscription", "exposure_state", "confidence", "source_coverage", "observed_at",
        "evaluated_at", "evidence_refs", "missing_inputs", "reason_codes", "fencing_token", "checkpoint",
    }
    assert required <= properties
    forbidden = {
        "raw_schema", "schema_body", "schema_source", "payload", "sample_record", "message_payload",
        "message_key", "credentials", "registry_token", "exception_text",
    }
    assert properties.isdisjoint(forbidden)
