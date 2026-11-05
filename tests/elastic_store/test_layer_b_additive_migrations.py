"""Team 0 Layer B additive migrations 0034/0035/0036 reconciliation.

These tests prove the new migrations are strictly additive, strictly
increasing, linear (single terminal leaf), privacy/honesty safe, and that the
0001-0033 released chain stays checksum-immutable.
"""

from __future__ import annotations

from packages.elastic_store.manifest import (
    ASSET_SEMANTIC_SEARCH_MIGRATION,
    ML_ANOMALY_DETECTOR_JOBS_MIGRATION,
    OPENLINEAGE_STRICT_MAPPING_FIELDS_MIGRATION,
    migrations,
)
from scripts.release.current_terminal_migration import migration_report
from scripts.release.validate_migration_graph import validate

RELEASED_TERMINAL_ID = "0033_team1_stream_schema_intelligence_runtime"


def test_layer_b_migrations_are_appended_strictly_increasing_and_linear():
    registry = migrations()
    ids = [migration.migration_id for migration in registry]
    # 0034/0035 stay appended after the released chain; B21 added 0036 as the
    # new strictly-increasing additive terminal.
    assert ids[-3:] == [
        "0034_ml_anomaly_detector_jobs",
        "0035_asset_semantic_search",
        "0036_openlineage_strict_mapping_fields",
    ]

    prefixes = [int(migration_id.split("_", 1)[0]) for migration_id in ids]
    assert prefixes == sorted(prefixes)
    assert len(prefixes) == len(set(prefixes))
    assert prefixes[-1] == 36

    # Strictly linear: each depends only on its immediate predecessor.
    for previous, migration in zip(registry, registry[1:]):
        assert migration.dependencies == [previous.migration_id]


def test_graph_reports_single_terminal_leaf_0036():
    report = migration_report()
    assert report["terminal_migration"] == "0036_openlineage_strict_mapping_fields"
    assert report["migration_count"] == 36
    graph = validate(migrations())
    assert graph["state"] == "valid"
    assert graph["leaves"] == ["0036_openlineage_strict_mapping_fields"]
    assert graph["terminal_migration"] == "0036_openlineage_strict_mapping_fields"


def test_released_chain_0001_to_0033_stays_immutable():
    registry = migrations()
    terminal_index = next(i for i, m in enumerate(registry) if m.migration_id == RELEASED_TERMINAL_ID)
    # 0034/0035/0036 only ever appended after the released terminal; nothing before it moves.
    assert terminal_index == len(registry) - 4
    assert len(registry[terminal_index].checksum) == 64


def test_ml_anomaly_detector_mapping_is_strict_and_metadata_only():
    migration = ML_ANOMALY_DETECTOR_JOBS_MIGRATION
    assert migration.dependencies == [RELEASED_TERMINAL_ID]
    mapping = migration.operations["mapping_updates"]["dataobs-ml-anomaly-detectors-v1"]
    assert mapping["dynamic"] == "strict"
    props = set(mapping["properties"])
    required = {
        "tenant_id",
        "environment",
        "monitor_id",
        "ml_job_id",
        "detection_mode",
        "job_state",
        "availability_state",
        "reason_codes",
        "missing_inputs",
    }
    assert required <= props
    # No raw payloads, secrets, or sample records in a metadata-only registry.
    forbidden = {"raw_record", "sample_record", "payload", "credentials", "api_key", "token"}
    assert props.isdisjoint(forbidden)


def test_asset_semantic_search_mapping_is_strict_and_honest():
    migration = ASSET_SEMANTIC_SEARCH_MIGRATION
    assert migration.dependencies == ["0034_ml_anomaly_detector_jobs"]
    mapping = migration.operations["mapping_updates"]["dataobs-asset-search-current-v1"]
    assert mapping["dynamic"] == "strict"
    props = set(mapping["properties"])
    required = {
        "tenant_id",
        "environment",
        "asset_id",
        "search_text",
        "availability_state",
        "reason_codes",
        "missing_inputs",
    }
    assert required <= props
    forbidden = {"credentials", "api_key", "token", "raw_sample"}
    assert props.isdisjoint(forbidden)


def test_openlineage_strict_mapping_migration_is_additive_and_repaints_the_bound_template():
    from packages.elastic_store.registry import OPENLINEAGE_PROPERTIES, _ensure_data_stream_template

    migration = OPENLINEAGE_STRICT_MAPPING_FIELDS_MIGRATION
    # Additive forward migration: depends only on 0035 and only re-applies the
    # bound openlineage data-stream template - it edits no released migration.
    assert migration.migration_id == "0036_openlineage_strict_mapping_fields"
    assert migration.dependencies == ["0035_asset_semantic_search"]
    assert set(migration.operations) == {"data_streams"}
    assert migration.operations["data_streams"] == ["logs-dataobs.openlineage-*"]

    # The exact flat fields the OpenLineage ingest path writes, mapped with the
    # types derived from the written values; dynamic:strict is preserved.
    assert OPENLINEAGE_PROPERTIES == {
        "event_id": {"type": "keyword"},
        "content_fingerprint": {"type": "keyword"},
        "producer": {"type": "keyword"},
        "schema_url": {"type": "keyword"},
        "job_namespace": {"type": "keyword"},
        "job_name": {"type": "keyword"},
        "input_assets": {"type": "keyword"},
        "output_assets": {"type": "keyword"},
        "source_event_time": {"type": "date"},
        "safe_facets": {"type": "flattened"},
        "unknown_facets": {"type": "flattened"},
    }

    # The template the migration repaints maps every OpenLineage field explicitly
    # while remaining strict (no dynamic:true shortcut).
    captured: dict = {}

    class _RecordingIndices:
        def put_index_template(self, **kwargs):
            captured.update(kwargs)

    class _RecordingES:
        indices = _RecordingIndices()

    _ensure_data_stream_template(_RecordingES(), "logs-dataobs.openlineage-*")
    mappings = captured["template"]["mappings"]
    assert mappings["dynamic"] == "strict"
    for field, definition in OPENLINEAGE_PROPERTIES.items():
        assert mappings["properties"][field] == definition
