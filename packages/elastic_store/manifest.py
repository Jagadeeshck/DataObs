from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

MIGRATION_STATE_INDEX = "dataobs-system-migrations-v1"
MUTABLE_INDICES = [
    "dataobs-tenants-v1",
    "dataobs-sources-v1",
    "dataobs-integrations-v1",
    "dataobs-collectors-v1",
    "dataobs-scanners-v1",
    "dataobs-scan-policies-v1",
    "dataobs-tasks-v1",
    "dataobs-task-leases-v1",
    "dataobs-idempotency-v1",
    "dataobs-assets-v1",
    "dataobs-schema-current-v1",
    "dataobs-freshness-current-v1",
    "dataobs-profile-current-v1",
    "dataobs-quality-current-v1",
    "dataobs-monitors-v1",
    "dataobs-incidents-v1",
    "dataobs-workflow-definitions-v1",
    "dataobs-ownership-v1",
]
DATA_STREAMS = [
    "logs-dataobs.audit-*",
    "logs-dataobs.scan_error-*",
    "logs-dataobs.scan_execution-*",
    "logs-dataobs.database_inventory-*",
    "logs-dataobs.openlineage-*",
    "logs-dataobs.schema_snapshot-*",
    "logs-dataobs.schema_change-*",
    "logs-dataobs.quality_result-*",
    "logs-dataobs.incident_event-*",
    "logs-dataobs.workflow_execution-*",
    "metrics-dataobs.freshness-*",
    "metrics-dataobs.table_profile-*",
    "metrics-dataobs.column_profile-*",
    "metrics-dataobs.collector_health-*",
    "metrics-dataobs.scanner_health-*",
    "traces-dataobs.jobs-*",
    "traces-dataobs.ai-*",
]
TRANSFORMS = [
    "dataobs-latest-collector-state",
    "dataobs-latest-scanner-state",
    "dataobs-latest-asset-state",
    "dataobs-current-incident-summary",
]

BASE_PROPERTIES: Dict[str, Any] = {
    "tenant_id": {"type": "keyword"},
    "environment": {"type": "keyword"},
    "@timestamp": {"type": "date"},
    "created_at": {"type": "date"},
    "updated_at": {"type": "date"},
    "source_id": {"type": "keyword"},
    "integration_id": {"type": "keyword"},
    "asset_id": {"type": "keyword"},
    "scanner_id": {"type": "keyword"},
    "task_id": {"type": "keyword"},
    "execution_id": {"type": "keyword"},
    "database": {"type": "keyword"},
    "schema": {"type": "keyword"},
    "table": {"type": "keyword"},
    "column": {"type": "keyword"},
    "asset_type": {"type": "keyword"},
    "schema_fingerprint": {"type": "keyword"},
    "state": {"type": "keyword"},
    "duration_ms": {"type": "long"},
    "retries": {"type": "integer"},
    "error_category": {"type": "keyword"},
    "owner_team": {"type": "keyword"},
    "business_service": {"type": "keyword"},
    "pillar": {"type": "keyword"},
    "schema_version": {"type": "keyword"},
    "status": {"type": "keyword"},
    "correlation_id": {"type": "keyword"},
    "trace_id": {"type": "keyword"},
    "run_id": {"type": "keyword"},
    "job_id": {"type": "keyword"},
    "classification": {"type": "keyword"},
    "labels": {"type": "flattened"},
    "annotations": {"type": "flattened"},
    "metadata": {"type": "flattened"},
}

INCIDENT_AUTOMATION_MUTABLE_INDICES = [
    "dataobs-findings-v1",
    "dataobs-incidents-v1",
    "dataobs-incident-correlations-v1",
    "dataobs-notification-policies-v1",
    "dataobs-workflow-definitions-v1",
    "dataobs-workflow-bindings-v1",
    "dataobs-workflow-executions-v1",
    "dataobs-action-approvals-v1",
    "dataobs-action-idempotency-v1",
    "dataobs-case-links-v1",
]

INCIDENT_AUTOMATION_STREAMS = [
    "logs-dataobs.finding-*",
    "logs-dataobs.incident_event-*",
    "logs-dataobs.correlation_event-*",
    "logs-dataobs.workflow_execution-*",
    "logs-dataobs.workflow_step-*",
    "logs-dataobs.approval_event-*",
    "logs-dataobs.notification_delivery-*",
    "logs-dataobs.remediation_action-*",
    "logs-dataobs.verification_event-*",
    "metrics-dataobs.incident-*",
    "metrics-dataobs.workflow-*",
]

INCIDENT_AUTOMATION_PROPERTIES: Dict[str, Any] = {
    "finding_id": {"type": "keyword"},
    "incident_id": {"type": "keyword"},
    "workflow_id": {"type": "keyword"},
    "workflow_execution_id": {"type": "keyword"},
    "step_id": {"type": "keyword"},
    "policy_id": {"type": "keyword"},
    "monitor_id": {"type": "keyword"},
    "rule_id": {"type": "keyword"},
    "kibana_space": {"type": "keyword"},
    "elastic_case_id": {"type": "keyword"},
    "external_incident_id": {"type": "keyword"},
    "finding_type": {"type": "keyword"},
    "signal_type": {"type": "keyword"},
    "incident_state": {"type": "keyword"},
    "severity": {"type": "keyword"},
    "deduplication_key": {"type": "keyword"},
    "correlation_key": {"type": "keyword"},
    "request_id": {"type": "keyword"},
    "span_id": {"type": "keyword"},
    "action_type": {"type": "keyword"},
    "risk_level": {"type": "keyword"},
    "approval_state": {"type": "keyword"},
    "retry_count": {"type": "integer"},
    "timeout_seconds": {"type": "integer"},
    "terminal_state": {"type": "boolean"},
    "technical_score": {"type": "double"},
    "business_impact_score": {"type": "double"},
    "affected_asset_count": {"type": "integer"},
    "downstream_asset_count": {"type": "integer"},
    "duration_ms": {"type": "long"},
    "event_version": {"type": "keyword"},
    "source_event_version": {"type": "keyword"},
    "first_observed_at": {"type": "date"},
    "last_observed_at": {"type": "date"},
    "opened_at": {"type": "date"},
    "acknowledged_at": {"type": "date"},
    "resolved_at": {"type": "date"},
    "closed_at": {"type": "date"},
    "expires_at": {"type": "date"},
}

KAFKA_MUTABLE_INDICES = [
    "dataobs-kafka-clusters-v1",
    "dataobs-kafka-brokers-v1",
    "dataobs-kafka-topics-v1",
    "dataobs-kafka-partitions-v1",
    "dataobs-kafka-consumer-groups-v1",
    "dataobs-kafka-connectors-v1",
    "dataobs-kafka-schemas-v1",
    "dataobs-pathway-nodes-v1",
    "dataobs-pathway-definitions-v1",
    "dataobs-pathway-slos-v1",
    "dataobs-stream-monitors-v1",
    "dataobs-collection-capabilities-v1",
    "dataobs-pathway-checkpoints-v1",
]
KAFKA_DATA_STREAMS = [
    "metrics-dataobs.kafka_broker-*",
    "metrics-dataobs.kafka_topic-*",
    "metrics-dataobs.kafka_partition-*",
    "metrics-dataobs.kafka_consumer_group-*",
    "metrics-dataobs.kafka_client-*",
    "metrics-dataobs.pathway_edge-*",
    "metrics-dataobs.pathway_full-*",
    "metrics-dataobs.pathway_internal-*",
    "metrics-dataobs.retention_risk-*",
    "logs-dataobs.kafka_inventory-*",
    "logs-dataobs.kafka_config_change-*",
    "logs-dataobs.kafka_schema_change-*",
    "logs-dataobs.kafka_connect-*",
    "logs-dataobs.stream_finding-*",
    "logs-dataobs.pathway_event-*",
    "logs-dataobs.pathway_slo-*",
]
KAFKA_PROPERTIES: Dict[str, Any] = (
    {
        key: {"type": "keyword"}
        for key in [
            "cluster_id",
            "broker_id",
            "topic_id",
            "partition_id",
            "consumer_group_id",
            "producer_service_id",
            "consumer_service_id",
            "source_node_id",
            "destination_node_id",
            "edge_id",
            "pathway_id",
            "pathway_type",
            "messaging_system",
            "lag_estimation_method",
            "connector_state",
            "task_state",
            "schema_subject",
            "schema_compatibility",
            "health_state",
            "source_document_ref",
            "collection_provider",
        ]
    }
    | {
        key: {"type": "double"}
        for key in [
            "p50_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
            "throughput_messages_per_second",
            "throughput_bytes_per_second",
            "payload_size_p50_bytes",
            "payload_size_p95_bytes",
            "lag_seconds",
            "lag_confidence",
            "consumer_rate",
            "producer_rate",
            "drain_time_seconds",
            "retention_risk_ratio",
            "estimated_data_loss_seconds",
            "error_rate",
            "retry_rate",
            "dlq_rate",
        ]
    }
    | {
        key: {"type": "long"}
        for key in [
            "partition",
            "current_offset",
            "high_offset",
            "earliest_offset",
            "lag_messages",
            "retention_ms",
            "retention_bytes",
            "offline_partition_count",
            "under_replicated_partition_count",
            "consumer_group_members",
            "rebalance_count",
            "schema_version_number",
        ]
    }
    | {
        "health_reasons": {"type": "keyword"},
        "replicas": {"type": "integer"},
        "isr": {"type": "integer"},
        "leader_id": {"type": "integer"},
    }
)


@dataclass(frozen=True)
class Migration:
    migration_id: str
    description: str
    schema_version: str
    dependencies: List[str] = field(default_factory=list)
    rollback_strategy: str = "delete aliases/templates created by this migration after human review"
    operations: Dict[str, Any] = field(default_factory=dict)

    @property
    def checksum(self) -> str:
        return hashlib.sha256(
            json.dumps(
                {
                    "id": self.migration_id,
                    "description": self.description,
                    "schema_version": self.schema_version,
                    "dependencies": self.dependencies,
                    "operations": self.operations,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()


FOUNDATION_MIGRATION = Migration(
    "0001_product_foundation",
    "Create product foundation mutable indices, data stream templates, aliases, lifecycle placeholders, and migration state",
    "v1",
    operations={"mutable_indices": MUTABLE_INDICES, "data_streams": DATA_STREAMS, "transforms": TRANSFORMS},
)

POSTGRES_OBSERVABILITY_MIGRATION = Migration(
    "0002_postgres_observability",
    "Add PostgreSQL observability task leases, idempotency, current-state indices, and append-only inventory/schema/freshness/profile/quality streams",
    "v1",
    dependencies=["0001_product_foundation"],
    operations={
        "mutable_indices": [
            "dataobs-task-leases-v1",
            "dataobs-idempotency-v1",
            "dataobs-schema-current-v1",
            "dataobs-freshness-current-v1",
            "dataobs-profile-current-v1",
            "dataobs-quality-current-v1",
        ],
        "data_streams": [
            "logs-dataobs.database_inventory-*",
            "logs-dataobs.schema_snapshot-*",
            "logs-dataobs.schema_change-*",
            "logs-dataobs.scan_execution-*",
            "logs-dataobs.scan_error-*",
            "logs-dataobs.audit-*",
            "logs-dataobs.quality_result-*",
            "metrics-dataobs.freshness-*",
            "metrics-dataobs.table_profile-*",
            "metrics-dataobs.column_profile-*",
            "metrics-dataobs.scanner_health-*",
        ],
    },
)


INCIDENT_AUTOMATION_MIGRATION = Migration(
    "0003_incident_automation",
    "Add incident automation findings, correlation, workflow, approval, notification and case-link indices and streams",
    "v1",
    dependencies=["0002_postgres_observability"],
    rollback_strategy="retain mutable incident state until explicit lifecycle/archive policy; remove templates only after snapshot validation",
    operations={
        "mutable_indices": INCIDENT_AUTOMATION_MUTABLE_INDICES,
        "data_streams": INCIDENT_AUTOMATION_STREAMS,
        "retention_defaults": {
            "findings_and_workflow_steps": "30d operational retention",
            "incident_and_audit_events": "365d compliance retention",
            "mutable_incident_state": "retained until explicit operator lifecycle/archive policy",
        },
    },
)

KAFKA_DSM_MIGRATION = Migration(
    "0004_kafka_data_streams_monitoring",
    "Add Kafka inventory, pathway projections, retention risk, SLO and collection capability state",
    "v1",
    dependencies=["0003_incident_automation"],
    rollback_strategy="stop Observer and Pathway Worker, snapshot state, then remove v1 aliases/templates; raw Elastic telemetry remains untouched",
    operations={
        "mutable_indices": KAFKA_MUTABLE_INDICES,
        "data_streams": KAFKA_DATA_STREAMS,
        "transforms": [
            "dataobs-latest-kafka-cluster-health",
            "dataobs-latest-topic-health",
            "dataobs-latest-consumer-group-health",
            "dataobs-latest-connector-health",
            "dataobs-latest-pathway-edge",
            "dataobs-current-pathway-health",
            "dataobs-current-retention-risk",
            "dataobs-current-pathway-slo",
        ],
    },
)


def migrations() -> List[Migration]:
    return [FOUNDATION_MIGRATION, POSTGRES_OBSERVABILITY_MIGRATION, INCIDENT_AUTOMATION_MIGRATION, KAFKA_DSM_MIGRATION]
