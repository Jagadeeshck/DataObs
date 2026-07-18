from packages.elastic_store.manifest import DATA_STREAMS, MUTABLE_INDICES
from packages.elastic_store.registry import plan


def test_migration_plan_contains_foundation_storage_patterns():
    p = plan()[0]
    assert p["migration_id"] == "0001_product_foundation"
    assert "checksum" in p
    assert "dataobs-assets-v1" in p["operations"]["mutable_indices"]
    assert "logs-dataobs.schema_snapshot-*" in p["operations"]["data_streams"]
    assert MUTABLE_INDICES and DATA_STREAMS
