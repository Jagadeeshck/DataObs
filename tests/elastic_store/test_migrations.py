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
    assert [item.migration_id for item in plan][-3:-1] == [
        "0004_kafka_data_streams_monitoring",
        "0005_console_foundation",
    ]
    assert plan[-2].dependencies == ["0004_kafka_data_streams_monitoring"]
    assert "dataobs-saved-views-v1" in plan[-2].operations["mutable_indices"]


def test_pathway_asset_360_is_forward_only_after_console_foundation():
    from packages.elastic_store.manifest import migrations

    migration = migrations()[-1]
    assert migration.migration_id == "0006_pathway_asset_360"
    assert migration.dependencies == ["0005_console_foundation"]
    assert "dataobs-pathway-monitors-v1" in migration.operations["mutable_indices"]
