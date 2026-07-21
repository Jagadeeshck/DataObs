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

    migration = next(m for m in migrations() if m.migration_id == "0011_incident_automation_workbench")
    assert migration.migration_id == "0011_incident_automation_workbench"
    assert migration.dependencies == ["0010_topic_queue_stream_360_completion"]
    assert "dataobs-remediation-actions-v1" in migration.operations["mutable_indices"]
    assert "logs-dataobs.remediation_action_audit-*" in migration.operations["data_streams"]


def test_incident_mapping_fix_is_forward_only_and_explicit():
    from packages.elastic_store.manifest import migrations

    migration = next(m for m in migrations() if m.migration_id == "0012_incident_mapping_and_occ_fix")
    assert migration.migration_id == "0012_incident_mapping_and_occ_fix"
    assert migration.dependencies == ["0011_incident_automation_workbench"]
    assert set(migration.operations["mapping_updates"]) == {
        "dataobs-findings-v1",
        "dataobs-incidents-v1",
    }


def test_released_migration_history_is_immutable():
    from packages.elastic_store.manifest import migrations

    expected = {
        "0001_product_foundation": "71d939094a97b4dd7c61de60542b60dd41cb238fd6bebfd75d53d723b00f3556",
        "0002_postgres_observability": "c2098fa24ddae209fcf2ffeb369f7040d57018d58682a8513db9e943c749aa2d",
        "0003_incident_automation": "f1f250822f94c5cc95c0b8547402a7a1294a8a3f04f1b8bd6b2713a643712ee5",
        "0004_kafka_data_streams_monitoring": "bf2a4cb663077d1df0be960300d04f4ad0ac2a43ab34fc0f01bf2fa40a1b32c6",
        "0005_console_foundation": "3b6861df951b1e4c46d0c2b6430e9327c6cf83533a7c908e0dca1cdde7793197",
        "0006_pathway_asset_360": "19dd1a7a5c6c36f3f807b13ca5d4785affc499cfbd53488c222b5a82b47faf10",
        "0007_automated_monitoring_data_products_rca": "827dd6e892a7199d4b6e91577cc3108b10045a0d67fc68375b088d20e412213e",
        "0008_job_run_observability": "ce32e272e9e5f7b30387cfdffbe17a403ce22fd2cffc947aea41bcddcd3e0ffe",
        "0009_topic_queue_stream_360": "6568576cd65fbf0f151674322506c17d95d8b361370e5a74e9bd972937eb8e95",
        "0010_topic_queue_stream_360_completion": "10230af88ce07b64b1e8d310065d2ae2461b4e09b8ef73c04fcf200a8f44d2cc",
        "0011_incident_automation_workbench": "e5ac77c3fb833c9e8380922d2d38c5e23409f1446afe6b131a137d272b6ce1aa",
    }
    released = migrations()[:11]
    assert [migration.migration_id for migration in released] == list(expected)
    assert {migration.migration_id: migration.checksum for migration in released} == expected


def test_strict_mapping_covers_every_serialized_incident_field():
    from packages.domain_model.incident import Finding, Incident
    from packages.elastic_store.registry import _mapping

    properties = _mapping()["properties"]
    assert _mapping()["dynamic"] == "strict"
    assert set(Finding.model_fields) <= set(properties)
    assert set(Incident.model_fields) - {"seq_no", "primary_term"} <= set(properties)
    assert "seq_no" not in properties
    assert "primary_term" not in properties
