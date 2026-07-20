from packages.elastic_store.manifest import DATA_STREAMS, MUTABLE_INDICES
from packages.elastic_store.registry import plan


def test_migration_plan_contains_foundation_storage_patterns():
    p = plan()[0]
    assert p["migration_id"] == "0001_product_foundation"
    assert "checksum" in p
    assert "dataobs-assets-v1" in p["operations"]["mutable_indices"]
    assert "logs-dataobs.schema_snapshot-*" in p["operations"]["data_streams"]
    assert MUTABLE_INDICES and DATA_STREAMS


def test_console_foundation_is_forward_only_after_original_kafka_migration():
    from packages.elastic_store.manifest import migrations

    plan = migrations()
    assert [item.migration_id for item in plan][3:5] == [
        "0004_kafka_data_streams_monitoring",
        "0005_console_foundation",
    ]
    assert plan[4].dependencies == ["0004_kafka_data_streams_monitoring"]
    assert "dataobs-saved-views-v1" in plan[4].operations["mutable_indices"]


def test_pathway_asset_360_is_forward_only_after_console_foundation():
    from packages.elastic_store.manifest import migrations

    migration = migrations()[5]
    assert migration.migration_id == "0006_pathway_asset_360"
    assert migration.dependencies == ["0005_console_foundation"]
    assert "dataobs-pathway-monitors-v1" in migration.operations["mutable_indices"]


def test_automated_monitoring_migration_is_forward_only_and_executable():
    from packages.elastic_store.manifest import migrations

    migration = next(m for m in migrations() if m.migration_id == "0007_automated_monitoring_data_products_rca")
    assert migration.migration_id == "0007_automated_monitoring_data_products_rca"
    assert migration.dependencies == ["0006_pathway_asset_360"]
    assert "dataobs-monitor-definitions-v2" in migration.operations["mutable_indices"]
    assert "dataobs-monitors-v1" not in migration.operations["mutable_indices"]
    assert all(isinstance(transform, dict) for transform in migration.operations["transforms"])
    assert all(
        {"id", "source", "destination", "unique_key", "sort"} <= transform.keys()
        for transform in migration.operations["transforms"]
    )


def test_stream_completion_installs_observer_coordination_and_evidence():
    from packages.elastic_store.manifest import migrations

    migration = next(item for item in migrations() if item.migration_id == "0010_topic_queue_stream_360_completion")
    assert migration.migration_id == "0010_topic_queue_stream_360_completion"
    assert migration.dependencies == ["0009_topic_queue_stream_360"]
    assert {
        "dataobs-kafka-observer-checkpoints-v1",
        "dataobs-kafka-observer-leases-v1",
        "dataobs-stream-collection-state-v1",
        "dataobs-stream-capability-state-v1",
    } <= set(migration.operations["mutable_indices"])
    assert {
        "metrics-dataobs.kafka-offset-snapshot-*",
        "metrics-dataobs.kafka-connect-*",
        "metrics-dataobs.kafka-schema-*",
        "logs-dataobs.stream-inspection-audit-*",
    } <= set(migration.operations["data_streams"])
    assert len(migration.operations["transforms"]) == 15
    assert all(
        {"id", "source", "destination", "unique_key", "sort"} <= transform.keys()
        for transform in migration.operations["transforms"]
    )


def test_incident_workbench_is_forward_only_after_immutable_0010():
    from packages.elastic_store.manifest import migrations

    migration = migrations()[-1]
    assert migration.migration_id == "0011_incident_automation_workbench"
    assert migration.dependencies == ["0010_topic_queue_stream_360_completion"]
    assert "dataobs-remediation-actions-v1" in migration.operations["mutable_indices"]
    assert "logs-dataobs.remediation_action_audit-*" in migration.operations["data_streams"]
