from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

DATA_PRODUCT_RECONCILIATION_EVIDENCE = (
    "contracts.xml",
    "unit.xml",
    "migrations.xml",
    "migration-clean-install.json",
    "migration-upgrade.json",
    "migration-repeat-apply.json",
    "mapping-contract.json",
    "retry-date-boundaries.json",
    "claim-expiry-boundaries.json",
    "resource-discriminator.json",
    "reservation-only-matrix.json",
    "proposal-immutable-replay.json",
    "dependency-token-recovery.json",
    "dependency-partial-write-matrix.json",
    "dependency-large-result.json",
    "dependency-detailed-result.json",
    "dependency-terminal-evidence.json",
    "dependency-two-worker-takeover.json",
    "lifecycle-crash-matrix.json",
    "lifecycle-revision-snapshot.json",
    "lifecycle-immutable-replay.json",
    "terminal-revisit.json",
    "cli-results.json",
    "elasticsearch.xml",
    "security.xml",
    "security-report.json",
    "sentinel-report.json",
    "redacted.log",
)

DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE = "data-product-runtime-foundation"
DATA_PRODUCT_RECONCILIATION_FULL_PROFILE = "data-product-reconciliation-full"
DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE = (
    "contracts.xml",
    "unit.xml",
    "migrations.xml",
    "elasticsearch.xml",
    "security.xml",
    "migration-clean-install.json",
    "migration-upgrade.json",
    "migration-repeat-apply.json",
    "mapping-contract.json",
    "retry-date-boundaries.json",
    "claim-expiry-boundaries.json",
    "resource-discriminator.json",
    "security-report.json",
    "sentinel-report.json",
    "redacted.log",
)

DATA_PRODUCT_ELASTICSEARCH_EVIDENCE = (
    "migrations.xml",
    "migration-clean-install.json",
    "migration-upgrade.json",
    "migration-repeat-apply.json",
    "mapping-contract.json",
    "retry-date-boundaries.json",
    "claim-expiry-boundaries.json",
    "resource-discriminator.json",
    "reservation-only-matrix.json",
    "proposal-immutable-replay.json",
    "dependency-token-recovery.json",
    "dependency-partial-write-matrix.json",
    "dependency-large-result.json",
    "dependency-detailed-result.json",
    "dependency-terminal-evidence.json",
    "dependency-two-worker-takeover.json",
    "lifecycle-crash-matrix.json",
    "lifecycle-revision-snapshot.json",
    "lifecycle-immutable-replay.json",
    "terminal-revisit.json",
    "cli-results.json",
    "elasticsearch.xml",
)

# Every JUnit emitted by a foundation producer is a required, validated artifact.
DATA_PRODUCT_FOUNDATION_JUNIT_EVIDENCE = (
    "contracts.xml",
    "unit.xml",
    "migrations.xml",
    "elasticsearch.xml",
    "security.xml",
)

# Artifact-specific execution policy.  Unit skips are limited to the two
# deliberately opt-in fixtures; hosted real-stack evidence must be skip-free.
DATA_PRODUCT_FOUNDATION_JUNIT_POLICIES = {
    "contracts.xml": {"allow_skips": False, "allowed_skip_reasons": (), "maximum_skips": 0},
    "unit.xml": {
        "allow_skips": True,
        "allowed_skip_reasons": (
            "hosted runtime secret only",
            "requires RUN_CERTIFICATION_TESTS=1 and the bounded live stack",
        ),
        "maximum_skips": 20,
    },
    "migrations.xml": {"allow_skips": False, "allowed_skip_reasons": (), "maximum_skips": 0},
    "elasticsearch.xml": {"allow_skips": False, "allowed_skip_reasons": (), "maximum_skips": 0},
    "security.xml": {"allow_skips": False, "allowed_skip_reasons": (), "maximum_skips": 0},
}

DATA_PRODUCT_SECURITY_EVIDENCE = (
    "security.xml",
    "security-report.json",
    "sentinel-report.json",
    "redacted.log",
)

# Explicit groups are intentional: inserting an artifact into the canonical
# inventory must never silently transfer ownership between producer jobs.
DATA_PRODUCT_EVIDENCE_OWNERS = {
    "contracts": ("contracts.xml",),
    "unit": ("unit.xml",),
    "elasticsearch": DATA_PRODUCT_ELASTICSEARCH_EVIDENCE,
    "security": DATA_PRODUCT_SECURITY_EVIDENCE,
}

DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS = {
    "contracts": ("contracts.xml",),
    "unit": ("unit.xml",),
    "elasticsearch": tuple(
        name
        for name in DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE
        if name not in {"contracts.xml", "unit.xml", *DATA_PRODUCT_SECURITY_EVIDENCE}
    ),
    "security": DATA_PRODUCT_SECURITY_EVIDENCE,
}

DATA_PRODUCT_EVIDENCE_PROFILES = {
    DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE: DATA_PRODUCT_RUNTIME_FOUNDATION_EVIDENCE,
    DATA_PRODUCT_RECONCILIATION_FULL_PROFILE: DATA_PRODUCT_RECONCILIATION_EVIDENCE,
}
# These are the only profiles accepted by both the builder and the independent
# verifier.  Keeping the tuple public gives workflow/contract tests one stable,
# ordered source for fail-closed profile dispatch.
SUPPORTED_DATA_PRODUCT_CERTIFICATION_PROFILES = (
    DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE,
    DATA_PRODUCT_RECONCILIATION_FULL_PROFILE,
)
# Security evidence is execution evidence for both profiles, never an optional
# metadata shell. The full profile permits additional valid executed controls.
DATA_PRODUCT_MINIMUM_SECURITY_CONTROLS = {
    DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE: 8,
    DATA_PRODUCT_RECONCILIATION_FULL_PROFILE: 1,
}
DATA_PRODUCT_EVIDENCE_OWNERS_BY_PROFILE = {
    DATA_PRODUCT_RUNTIME_FOUNDATION_PROFILE: DATA_PRODUCT_FOUNDATION_EVIDENCE_OWNERS,
    DATA_PRODUCT_RECONCILIATION_FULL_PROFILE: DATA_PRODUCT_EVIDENCE_OWNERS,
}


def data_product_evidence_inventory(profile: str) -> tuple[str, ...]:
    """Return an explicit certification inventory; unknown profiles fail closed."""
    try:
        return DATA_PRODUCT_EVIDENCE_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"unknown Data Product certification profile: {profile}") from exc


def data_product_evidence_owners(profile: str) -> dict[str, tuple[str, ...]]:
    try:
        return DATA_PRODUCT_EVIDENCE_OWNERS_BY_PROFILE[profile]
    except KeyError as exc:
        raise ValueError(f"unknown Data Product certification profile: {profile}") from exc


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

SECURITY_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "binding_id",
            "issuer",
            "principal_type",
            "principal_id",
            "created_by",
            "updated_by",
            "etag",
            "event_type",
            "event_action",
            "event_outcome",
            "reason_code",
            "principal_subject",
            "required_permission",
            "resource_type",
            "resource_id",
            "source_address",
            "user_agent_classification",
            "authorisation_source",
        ]
    },
    "environments": {"type": "keyword"},
    "roles": {"type": "keyword"},
    "active": {"type": "boolean"},
    "description": {"type": "match_only_text"},
    "revision": {"type": "long"},
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
    # Canonical Finding and Incident documents are stored directly in the mutable
    # indices. Keep this list in sync with packages.domain_model.incident because
    # the shared index mapping is deliberately strict.
    **{
        key: {"type": "keyword"}
        for key in [
            "source_event_id",
            "priority",
            "urgency",
            "impact",
            "primary_resource",
            "commander",
            "correlation_version",
            "elastic_case_version",
            "notification_state",
            "resolution_reason",
            "state_reason",
            "recovery_state",
            "recurrence_of",
            "split_from",
            "workflow_ref",
        ]
    },
    "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
    "summary": {"type": "match_only_text"},
    "impact_summary": {"type": "match_only_text"},
    "observed_value": {"type": "flattened"},
    "expected_value": {"type": "flattened"},
    "correlation_features": {"type": "flattened"},
    "correlation_explanation": {"type": "flattened"},
    "severity_factors": {"type": "flattened"},
    "evidence": {"type": "flattened"},
    "most_recent_evidence": {"type": "flattened"},
    "root_cause_candidates": {"type": "flattened"},
    "recovery_evidence": {"type": "flattened"},
    "confidence": {"type": "double"},
    "occurrence_count": {"type": "long"},
    "recovery_signal": {"type": "boolean"},
    "suppressed_until": {"type": "date"},
    "recovered_at": {"type": "date"},
    "reopened_at": {"type": "date"},
    **{
        key: {"type": "keyword"}
        for key in [
            "resource_ids",
            "data_product_ids",
            "downstream_impact",
            "finding_ids",
            "affected_assets",
            "responders",
            "watchers",
            "tags",
            "business_services",
            "merged_from",
        ]
    },
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
            "member_id",
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
            "lag_method",
            "retention_risk_state",
            "finding_state",
            "finding_reason",
            "connector_id",
            "schema_id",
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
            "confidence",
            "backlog_age_seconds",
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
            "sample_count",
            "partition_count",
            "replication_factor",
        ]
    }
    | {
        "health_reasons": {"type": "keyword"},
        "replicas": {"type": "integer"},
        "isr": {"type": "integer"},
        "leader_id": {"type": "integer"},
        "leader_available": {"type": "boolean"},
        "offline_replicas": {"type": "integer"},
        "source_trace_ids": {"type": "keyword"},
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
            "dataobs-latest-partition-health",
            "dataobs-latest-consumer-group-health",
            "dataobs-latest-connector-health",
            "dataobs-latest-schema-state",
            "dataobs-latest-pathway-edge",
            "dataobs-current-pathway-health",
            "dataobs-current-retention-risk",
            "dataobs-current-pathway-slo",
        ],
    },
)

CONSOLE_FOUNDATION_MIGRATION = Migration(
    "0005_console_foundation",
    "Add durable Console saved views, preferences, topology and command-center projections",
    "v1",
    dependencies=["0004_kafka_data_streams_monitoring"],
    rollback_strategy="disable Console writers, snapshot user state, then remove only the v1 Console aliases and templates",
    operations={
        "mutable_indices": [
            "dataobs-saved-views-v1",
            "dataobs-ui-preferences-v1",
            "dataobs-topology-summary-v1",
            "dataobs-command-center-summary-v1",
        ],
        "data_streams": ["logs-dataobs.console_event-*"],
        "transforms": ["dataobs-current-topology-summary", "dataobs-current-command-center-summary"],
    },
)

PATHWAY_ASSET_360_MIGRATION = Migration(
    "0006_pathway_asset_360",
    "Add pathway monitors, asset investigation projections, lineage and comparison state",
    "v1",
    dependencies=["0005_console_foundation"],
    rollback_strategy="disable product-query mutations, snapshot v1 state, and remove only 0006 aliases and templates",
    operations={
        "mutable_indices": [
            "dataobs-pathway-monitors-v1",
            "dataobs-asset-slos-v1",
            "dataobs-asset-annotations-v1",
            "dataobs-asset-usage-current-v1",
            "dataobs-lineage-current-v1",
            "dataobs-pathway-comparisons-v1",
        ],
        "data_streams": [
            "metrics-dataobs.asset_usage-*",
            "metrics-dataobs.asset_health-*",
            "metrics-dataobs.pathway_bottleneck-*",
            "logs-dataobs.asset_change-*",
            "logs-dataobs.pathway_monitor_result-*",
        ],
        "retention_defaults": {
            "usage_and_health_metrics": "90d operational retention",
            "asset_changes_and_monitor_results": "365d audit retention",
            "mutable_definitions": "retained until operator-managed archival",
        },
    },
)

AUTOMATED_MONITORING_MIGRATION = Migration(
    "0007_automated_monitoring_data_products_rca",
    "Add versioned monitors, baselines, recommendations, Data Products, reliability scorecards and explainable RCA",
    "v1",
    dependencies=["0006_pathway_asset_360"],
    rollback_strategy="stop v2 writers, retain append-only evidence, snapshot state, then repoint aliases after human review",
    operations={
        "mutable_indices": [
            "dataobs-monitor-definitions-v2",
            "dataobs-monitor-baselines-v1",
            "dataobs-monitor-recommendations-v1",
            "dataobs-monitor-suppressions-v1",
            "dataobs-monitor-evaluation-state-v1",
            "dataobs-monitor-coverage-v1",
            "dataobs-data-products-v1",
            "dataobs-data-product-membership-v1",
            "dataobs-data-product-slos-v1",
            "dataobs-data-product-scorecards-v1",
            "dataobs-rca-investigations-v1",
            "dataobs-rca-hypotheses-v1",
            "dataobs-rca-evidence-links-v1",
            "dataobs-code-change-events-v1",
            "dataobs-deployment-events-v1",
        ],
        "data_streams": [
            "metrics-dataobs.monitor-observation-*",
            "metrics-dataobs.monitor-evaluation-*",
            "metrics-dataobs.monitor-baseline-*",
            "metrics-dataobs.monitor-coverage-*",
            "metrics-dataobs.data-product-reliability-*",
            "logs-dataobs.monitor-finding-*",
            "logs-dataobs.monitor-recommendation-event-*",
            "logs-dataobs.rca-investigation-*",
            "logs-dataobs.rca-evidence-*",
            "logs-dataobs.code-change-*",
            "logs-dataobs.deployment-change-*",
        ],
        "transforms": [
            {
                "id": "dataobs-latest-monitor-state",
                "source": "metrics-dataobs.monitor-evaluation-*",
                "destination": "dataobs-monitor-evaluation-state-v1",
                "unique_key": ["tenant_id", "environment", "monitor_id"],
                "sort": "evaluation_timestamp",
            },
            {
                "id": "dataobs-latest-baseline",
                "source": "metrics-dataobs.monitor-baseline-*",
                "destination": "dataobs-monitor-baselines-v1",
                "unique_key": ["tenant_id", "environment", "monitor_id"],
                "sort": "baseline_timestamp",
            },
            {
                "id": "dataobs-current-asset-coverage",
                "source": "metrics-dataobs.monitor-coverage-*",
                "destination": "dataobs-monitor-coverage-v1",
                "unique_key": ["tenant_id", "environment", "asset_id"],
                "sort": "evaluation_timestamp",
            },
            {
                "id": "dataobs-current-product-reliability",
                "source": "metrics-dataobs.data-product-reliability-*",
                "destination": "dataobs-data-product-scorecards-v1",
                "unique_key": ["tenant_id", "environment", "product_id"],
                "sort": "evaluation_timestamp",
            },
            {
                "id": "dataobs-open-monitor-findings",
                "source": "logs-dataobs.monitor-finding-*",
                "destination": "dataobs-findings-v1",
                "unique_key": ["tenant_id", "environment", "finding_id"],
                "sort": "evaluation_timestamp",
            },
            {
                "id": "dataobs-latest-rca-investigation",
                "source": "logs-dataobs.rca-investigation-*",
                "destination": "dataobs-rca-investigations-v1",
                "unique_key": ["tenant_id", "environment", "investigation_id"],
                "sort": "updated_at",
            },
            {
                "id": "dataobs-latest-rca-hypothesis",
                "source": "logs-dataobs.rca-evidence-*",
                "destination": "dataobs-rca-hypotheses-v1",
                "unique_key": ["tenant_id", "environment", "hypothesis_id"],
                "sort": "updated_at",
            },
        ],
    },
)

JOB_RUN_OBSERVABILITY_MIGRATION = Migration(
    "0008_job_run_observability",
    "Add OpenLineage-native job, run, task, Spark stage, streaming, comparison and safe action projections",
    "v1",
    dependencies=["0007_automated_monitoring_data_products_rca"],
    rollback_strategy="stop job observers, retain append-only evidence, snapshot current projections, then remove only 0008 aliases/templates",
    operations={
        "mutable_indices": [
            "dataobs-job-definitions-v1",
            "dataobs-job-current-v1",
            "dataobs-job-schedules-v1",
            "dataobs-job-run-current-v1",
            "dataobs-task-run-current-v1",
            "dataobs-stage-run-current-v1",
            "dataobs-streaming-query-current-v1",
            "dataobs-run-attempt-current-v1",
            "dataobs-run-comparison-v1",
            "dataobs-job-slo-v1",
            "dataobs-job-monitor-link-v1",
            "dataobs-run-action-policy-v1",
            "dataobs-run-action-request-v1",
            "dataobs-job-source-state-v1",
            "dataobs-job-runtime-checkpoints-v1",
        ],
        "data_streams": [
            "logs-dataobs.openlineage-*",
            "logs-dataobs.job-run-*",
            "logs-dataobs.task-run-*",
            "logs-dataobs.stage-run-*",
            "logs-dataobs.run-attempt-*",
            "logs-dataobs.run-change-*",
            "logs-dataobs.run-action-audit-*",
            "metrics-dataobs.job-run-*",
            "metrics-dataobs.task-run-*",
            "metrics-dataobs.spark-stage-*",
            "metrics-dataobs.spark-task-*",
            "metrics-dataobs.spark-executor-*",
            "metrics-dataobs.streaming-query-*",
            "metrics-dataobs.job-resource-*",
            "metrics-dataobs.job-cost-*",
        ],
        "transforms": [
            {
                "id": "dataobs-latest-job-state",
                "source": "logs-dataobs.job-run-*",
                "destination": "dataobs-job-current-v1",
                "unique_key": ["tenant_id", "environment", "job_id"],
                "sort": "@timestamp",
            },
            {
                "id": "dataobs-latest-run-per-job",
                "source": "logs-dataobs.job-run-*",
                "destination": "dataobs-job-run-current-v1",
                "unique_key": ["tenant_id", "environment", "job_id", "run_id"],
                "sort": "@timestamp",
            },
            {
                "id": "dataobs-current-task-state",
                "source": "logs-dataobs.task-run-*",
                "destination": "dataobs-task-run-current-v1",
                "unique_key": ["tenant_id", "environment", "run_id", "task_id"],
                "sort": "@timestamp",
            },
            {
                "id": "dataobs-current-spark-stage",
                "source": "logs-dataobs.stage-run-*",
                "destination": "dataobs-stage-run-current-v1",
                "unique_key": ["tenant_id", "environment", "run_id", "stage_id"],
                "sort": "@timestamp",
            },
            {
                "id": "dataobs-current-streaming-query",
                "source": "metrics-dataobs.streaming-query-*",
                "destination": "dataobs-streaming-query-current-v1",
                "unique_key": ["tenant_id", "environment", "run_id", "streaming_query_id"],
                "sort": "@timestamp",
            },
        ],
        "retention_defaults": {"raw_events": "30d", "runtime_metrics": "90d", "action_audit": "365d"},
    },
)

STREAM_360_MUTABLE_INDICES = [
    "dataobs-stream-clusters-v1",
    "dataobs-stream-resources-v1",
    "dataobs-stream-partitions-v1",
    "dataobs-consumer-groups-v1",
    "dataobs-consumer-members-v1",
    "dataobs-stream-applications-v1",
    "dataobs-stream-connectors-v1",
    "dataobs-stream-connector-tasks-v1",
    "dataobs-schema-subjects-v1",
    "dataobs-schema-versions-v1",
    "dataobs-stream-config-current-v1",
    "dataobs-stream-offset-current-v1",
    "dataobs-stream-retention-risk-current-v1",
    "dataobs-stream-health-current-v1",
    "dataobs-stream-action-policy-v1",
    "dataobs-stream-action-request-v1",
    "dataobs-message-inspection-policy-v1",
    "dataobs-stream-source-state-v1",
]
STREAM_360_DATA_STREAMS = [
    *(
        f"metrics-dataobs.{name}-*"
        for name in (
            "stream-cluster",
            "stream-broker",
            "stream-topic",
            "stream-partition",
            "consumer-group",
            "consumer-member",
            "stream-application",
            "stream-connector",
            "stream-pathway",
            "stream-retention-risk",
        )
    ),
    *(
        f"logs-dataobs.{name}-*"
        for name in (
            "stream-inventory",
            "stream-config-change",
            "stream-schema-change",
            "stream-rebalance",
            "stream-connector-event",
            "stream-action-audit",
            "message-inspection-audit",
        )
    ),
]


def _stream_transform(name: str, source: str, destination: str, keys: list[str]) -> dict[str, Any]:
    return {
        "id": f"dataobs-current-{name}",
        "source": source,
        "destination": destination,
        "unique_key": ["tenant_id", "environment", *keys],
        "sort": "@timestamp",
    }


TOPIC_QUEUE_STREAM_360_MIGRATION = Migration(
    "0009_topic_queue_stream_360",
    "Add provider-neutral Stream 360 inventory, intelligence, safe actions, Connect and schema projections",
    "v1",
    dependencies=["0008_job_run_observability"],
    rollback_strategy="stop stream observers/transforms, retain append-only evidence, snapshot projections, then remove only 0009 aliases/templates",
    operations={
        "mutable_indices": STREAM_360_MUTABLE_INDICES,
        "data_streams": STREAM_360_DATA_STREAMS,
        "transforms": [
            _stream_transform(
                "stream-cluster", "metrics-dataobs.stream-cluster-*", "dataobs-stream-clusters-v1", ["cluster_id"]
            ),
            _stream_transform(
                "stream-topic",
                "metrics-dataobs.stream-topic-*",
                "dataobs-stream-resources-v1",
                ["cluster_id", "topic_id"],
            ),
            _stream_transform(
                "stream-partition",
                "metrics-dataobs.stream-partition-*",
                "dataobs-stream-partitions-v1",
                ["cluster_id", "topic_id", "partition_id"],
            ),
            _stream_transform(
                "consumer-group",
                "metrics-dataobs.consumer-group-*",
                "dataobs-consumer-groups-v1",
                ["cluster_id", "consumer_group_id"],
            ),
            _stream_transform(
                "stream-connector",
                "metrics-dataobs.stream-connector-*",
                "dataobs-stream-connectors-v1",
                ["cluster_id", "connector_id"],
            ),
            _stream_transform(
                "stream-offset",
                "metrics-dataobs.consumer-group-*",
                "dataobs-stream-offset-current-v1",
                ["cluster_id", "topic_id", "partition_id", "consumer_group_id"],
            ),
            _stream_transform(
                "retention-risk",
                "metrics-dataobs.stream-retention-risk-*",
                "dataobs-stream-retention-risk-current-v1",
                ["cluster_id", "topic_id", "partition_id", "consumer_group_id"],
            ),
            _stream_transform(
                "stream-application",
                "metrics-dataobs.stream-application-*",
                "dataobs-stream-applications-v1",
                ["cluster_id", "service_id"],
            ),
            _stream_transform(
                "stream-health",
                "metrics-dataobs.stream-topic-*",
                "dataobs-stream-health-current-v1",
                ["cluster_id", "topic_id"],
            ),
        ],
        "retention_defaults": {"inventory_and_audit": "365d", "operational_metrics": "90d"},
    },
)

STREAM_360_COMPLETION_INDICES = [
    "dataobs-kafka-observer-checkpoints-v1",
    "dataobs-kafka-observer-leases-v1",
    "dataobs-stream-collection-state-v1",
    "dataobs-stream-capability-state-v1",
    "dataobs-stream-application-current-v1",
    "dataobs-stream-rebalance-current-v1",
    "dataobs-stream-schema-impact-current-v1",
    "dataobs-stream-connector-health-current-v1",
    "dataobs-stream-monitor-current-v1",
    "dataobs-stream-action-current-v1",
    "dataobs-stream-comparison-v1",
]

STREAM_360_COMPLETION_STREAMS = [
    "metrics-dataobs.kafka-observer-runtime-*",
    "metrics-dataobs.kafka-offset-snapshot-*",
    "metrics-dataobs.kafka-group-snapshot-*",
    "metrics-dataobs.kafka-replication-health-*",
    "metrics-dataobs.kafka-rebalance-*",
    "metrics-dataobs.kafka-connect-*",
    "metrics-dataobs.kafka-schema-*",
    "logs-dataobs.kafka-collection-error-*",
    "logs-dataobs.stream-action-request-*",
    "logs-dataobs.stream-action-result-*",
    "logs-dataobs.stream-inspection-audit-*",
]

TOPIC_QUEUE_STREAM_360_COMPLETION_MIGRATION = Migration(
    "0010_topic_queue_stream_360_completion",
    "Install durable observer coordination, append-only evidence, and executable current-state projections",
    "v1",
    dependencies=["0009_topic_queue_stream_360"],
    rollback_strategy="stop observer and completion transforms; retain append-only evidence; snapshot then remove only 0010 aliases",
    operations={
        "mutable_indices": STREAM_360_COMPLETION_INDICES,
        "data_streams": STREAM_360_COMPLETION_STREAMS,
        "transforms": [
            _stream_transform(
                "kafka-cluster", "metrics-dataobs.stream-cluster-*", "dataobs-stream-clusters-v1", ["cluster_id"]
            ),
            _stream_transform(
                "kafka-broker",
                "metrics-dataobs.stream-broker-*",
                "dataobs-kafka-brokers-v1",
                ["cluster_id", "broker_id"],
            ),
            _stream_transform(
                "kafka-topic",
                "metrics-dataobs.stream-topic-*",
                "dataobs-stream-resources-v1",
                ["cluster_id", "topic_id"],
            ),
            _stream_transform(
                "kafka-partition",
                "metrics-dataobs.stream-partition-*",
                "dataobs-stream-partitions-v1",
                ["cluster_id", "topic_id", "partition_id"],
            ),
            _stream_transform(
                "kafka-group",
                "metrics-dataobs.kafka-group-snapshot-*",
                "dataobs-consumer-groups-v1",
                ["cluster_id", "consumer_group_id"],
            ),
            _stream_transform(
                "kafka-member",
                "metrics-dataobs.kafka-group-snapshot-*",
                "dataobs-consumer-members-v1",
                ["cluster_id", "consumer_group_id", "member_id"],
            ),
            _stream_transform(
                "kafka-offset-lag",
                "metrics-dataobs.kafka-offset-snapshot-*",
                "dataobs-stream-offset-current-v1",
                ["cluster_id", "topic_id", "partition_id", "consumer_group_id"],
            ),
            _stream_transform(
                "kafka-lag-velocity",
                "metrics-dataobs.kafka-offset-snapshot-*",
                "dataobs-stream-health-current-v1",
                ["cluster_id", "topic_id", "consumer_group_id"],
            ),
            _stream_transform(
                "kafka-drain-time",
                "metrics-dataobs.kafka-offset-snapshot-*",
                "dataobs-stream-collection-state-v1",
                ["cluster_id", "topic_id", "consumer_group_id"],
            ),
            _stream_transform(
                "kafka-retention-risk",
                "metrics-dataobs.stream-retention-risk-*",
                "dataobs-stream-retention-risk-current-v1",
                ["cluster_id", "topic_id", "partition_id", "consumer_group_id"],
            ),
            _stream_transform(
                "kafka-connector-task",
                "metrics-dataobs.kafka-connect-*",
                "dataobs-stream-connector-health-current-v1",
                ["cluster_id", "connector_id", "task_id"],
            ),
            _stream_transform(
                "kafka-schema-version",
                "metrics-dataobs.kafka-schema-*",
                "dataobs-stream-schema-impact-current-v1",
                ["cluster_id", "schema_subject", "schema_id"],
            ),
            _stream_transform(
                "kafka-application",
                "metrics-dataobs.stream-application-*",
                "dataobs-stream-application-current-v1",
                ["cluster_id", "service_id"],
            ),
            _stream_transform(
                "kafka-stream-health",
                "metrics-dataobs.kafka-replication-health-*",
                "dataobs-stream-health-current-v1",
                ["cluster_id", "topic_id"],
            ),
            _stream_transform(
                "kafka-monitor-link",
                "logs-dataobs.stream-finding-*",
                "dataobs-stream-monitor-current-v1",
                ["monitor_id", "incident_id"],
            ),
        ],
        "retention_defaults": {"operational_metrics": "90d", "audit": "365d"},
    },
)


INCIDENT_AUTOMATION_WORKBENCH_MIGRATION = Migration(
    "0011_incident_automation_workbench",
    "Complete durable collaboration, approval, action, verification and post-incident projections",
    "v1",
    dependencies=["0010_topic_queue_stream_360_completion"],
    rollback_strategy="stop workbench writers and transforms; retain append-only evidence; snapshot mutable projections before removing only 0011 resources",
    operations={
        # Existing 0003 v1 resources are reused. These resources represent genuinely
        # absent collaboration, safety, verification, and learning projections.
        "mutable_indices": [
            "dataobs-incident-assignments-v1",
            "dataobs-incident-watchers-v1",
            "dataobs-incident-tasks-v1",
            "dataobs-incident-suppressions-v1",
            "dataobs-incident-maintenance-windows-v1",
            "dataobs-incident-timeline-current-v1",
            "dataobs-incident-impact-current-v1",
            "dataobs-action-policies-v1",
            "dataobs-remediation-actions-v1",
            "dataobs-action-verifications-v1",
            "dataobs-case-sync-state-v1",
            "dataobs-post-incident-reviews-v1",
            "dataobs-post-incident-action-items-v1",
        ],
        "data_streams": [
            "logs-dataobs.incident_assignment-*",
            "logs-dataobs.incident_comment-*",
            "logs-dataobs.incident_merge_split-*",
            "logs-dataobs.incident_suppression-*",
            "logs-dataobs.case_sync-*",
            "logs-dataobs.action_policy_decision-*",
            "logs-dataobs.remediation_action_audit-*",
            "logs-dataobs.post_incident_review-*",
            "metrics-dataobs.incident_response-*",
            "metrics-dataobs.automation_effectiveness-*",
        ],
        "retention_defaults": {"audit_and_review": "365d", "operational_metrics": "90d"},
    },
)

# This is intentionally a forward operation rather than a change to the mapping
# helper used by released migrations.  Elasticsearch permits these properties to
# be added to an existing strict mapping without reindexing.
INCIDENT_MAPPING_AND_OCC_FIX_MIGRATION = Migration(
    "0012_incident_mapping_and_occ_fix",
    "Upgrade existing incident and finding mappings and record incident concurrency stabilization",
    "v1",
    dependencies=["0011_incident_automation_workbench"],
    rollback_strategy="retain additive mappings and documents; restore writers from snapshot only after operator review",
    operations={
        "mapping_updates": {
            "dataobs-findings-v1": INCIDENT_AUTOMATION_PROPERTIES,
            "dataobs-incidents-v1": INCIDENT_AUTOMATION_PROPERTIES,
        }
    },
)

MONITOR_RUNTIME_COMPLETION_MIGRATION = Migration(
    "0013_monitor_runtime_completion",
    "Add durable monitor definition history, scheduling, fenced leases, checkpoints and runtime audit evidence",
    "v1",
    dependencies=["0012_incident_mapping_and_occ_fix"],
    rollback_strategy="stop monitor-runtime writers; retain immutable evidence and snapshot runtime state before alias removal",
    operations={
        "mutable_indices": [
            "dataobs-monitor-definition-history-v1",
            "dataobs-monitor-schedules-v1",
            "dataobs-monitor-runtime-leases-v1",
            "dataobs-monitor-runtime-checkpoints-v1",
            "dataobs-monitor-baseline-history-v1",
            "dataobs-monitor-runtime-state-v1",
            "dataobs-monitor-idempotency-v1",
        ],
        "data_streams": [
            "logs-dataobs.monitor-definition-event-*",
            "logs-dataobs.monitor-runtime-event-*",
            "logs-dataobs.monitor-suppression-event-*",
        ],
        "retention_defaults": {"runtime_events": "90d", "definition_and_suppression_audit": "365d"},
    },
)

DATA_PRODUCT_360_COMPLETION_MIGRATION = Migration(
    "0014_data_product_360_completion",
    "Add durable Data Product revisions, reviewed membership, dependencies, SLO evaluations, coverage and impact",
    "v1",
    dependencies=["0013_monitor_runtime_completion"],
    rollback_strategy="stop Data Product writers and reliability transform; retain immutable events; snapshot then remove only 0014 resources",
    operations={
        # 0007 Data Product definitions, membership, SLOs, scorecards and
        # reliability stream are deliberately reused rather than recreated.
        "mutable_indices": [
            "dataobs-data-product-revisions-v1",
            "dataobs-data-product-membership-proposals-v1",
            "dataobs-data-product-membership-decisions-v1",
            "dataobs-data-product-dependency-current-v1",
            "dataobs-data-product-slo-evaluations-v1",
            "dataobs-data-product-coverage-v1",
            "dataobs-data-product-impact-current-v1",
            "dataobs-data-product-operation-state-v1",
            "dataobs-data-product-idempotency-v1",
        ],
        "data_streams": [
            "logs-dataobs.data-product-event-*",
            "logs-dataobs.data-product-membership-event-*",
            "logs-dataobs.data-product-slo-event-*",
            "logs-dataobs.data-product-impact-event-*",
        ],
        "transforms": [
            {
                "id": "dataobs-current-product-reliability",
                "source": "metrics-dataobs.data-product-reliability-*",
                "destination": "dataobs-data-product-scorecards-v1",
                "unique_key": ["tenant_id", "environment", "product_id"],
                "sort": "evaluation_timestamp",
            }
        ],
        "retention_defaults": {"events": "365d", "evaluations": "365d"},
    },
)

DATA_PRODUCT_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "id",
            "tenant_id",
            "environment",
            "schema_version",
            "etag",
            "name",
            "domain",
            "criticality",
            "lifecycle_state",
            "source_id",
            "integration_id",
            "owner_team",
            "business_service",
            "pillar",
            "status",
            "correlation_id",
        ]
    },
    "description": {"type": "text"},
    "revision": {"type": "integer"},
    "created_at": {"type": "date"},
    "updated_at": {"type": "date"},
    "tags": {"type": "keyword"},
    "labels": {"type": "flattened"},
    "annotations": {"type": "flattened"},
    "owner": {
        "properties": {
            "team": {"type": "keyword"},
            "support_url": {"type": "keyword"},
            "on_call_url": {"type": "keyword"},
        }
    },
    "outputs": {
        "type": "nested",
        "properties": {
            "entity_id": {"type": "keyword"},
            "entity_type": {"type": "keyword"},
            "display_name": {"type": "text"},
            "primary": {"type": "boolean"},
            "evidence_refs": {"type": "keyword"},
            "lineage_evidence_refs": {"type": "keyword"},
            "observed_at": {"type": "date"},
        },
    },
    # Compatibility collections are serialized by DataProductDefinition and must
    # therefore remain explicitly admitted even though production stores them separately.
    "members": {"type": "flattened"},
    "dependencies": {"type": "flattened"},
    "slos": {"type": "flattened"},
}

DATA_PRODUCT_EVENT_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "operation_id",
            "product_id",
            "tenant_id",
            "environment",
            "etag",
            "definition_checksum",
            "actor",
            "reason",
            "action",
            "outcome",
            "error_code",
        ]
    },
    "revision": {"type": "integer"},
    "occurred_at": {"type": "date"},
    "applied_at": {"type": "date"},
    "document": {"type": "flattened"},
}

DATA_PRODUCT_AUXILIARY_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "membership_id",
            "proposal_id",
            "product_id",
            "tenant_id",
            "environment",
            "entity_id",
            "entity_type",
            "source",
            "membership_source",
            "state",
            "actor",
            "reason",
            "slo_id",
            "component",
            "window",
            "evaluation_method",
            "etag",
            "overall_state",
            "trend",
        ]
    },
    **{key: {"type": "integer"} for key in ["proposal_revision", "definition_revision", "revision"]},
    **{
        key: {"type": "double"}
        for key in [
            "confidence",
            "source_coverage",
            "objective",
            "weight",
            "actual_value",
            "denominator",
            "coverage",
            "overall_score",
            "value",
        ]
    },
    "critical": {"type": "boolean"},
    "truncated": {"type": "boolean"},
    **{key: {"type": "date"} for key in ["observed_at", "decided_at", "window_start", "window_end", "evaluated_at"]},
    **{
        key: {"type": "keyword"}
        for key in [
            "evidence_refs",
            "source_monitor_ids",
            "source_evaluation_refs",
            "exclusions",
            "missing_evidence",
            "missing_components",
            "stale_components",
            "outputs",
            "members",
            "upstream_products",
            "downstream_products",
            "pathways",
            "known_consumers",
            "missing_dimensions",
        ]
    },
    "component_values": {"type": "flattened"},
    "component_weights": {"type": "flattened"},
    "formula": {"type": "keyword"},
    "observed_period": {"type": "keyword"},
}

DATA_PRODUCT_360_PRODUCTIZATION_MIGRATION = Migration(
    "0015_data_product_360_productization",
    "Install writer-complete strict Data Product mappings and readiness resources",
    "v1",
    dependencies=["0014_data_product_360_completion"],
    rollback_strategy="stop Data Product writers; retain additive mappings and immutable evidence",
    operations={
        "mapping_updates": {
            "dataobs-data-products-v1": DATA_PRODUCT_PROPERTIES,
            "dataobs-data-product-revisions-v1": DATA_PRODUCT_EVENT_PROPERTIES,
            "dataobs-data-product-operation-state-v1": DATA_PRODUCT_EVENT_PROPERTIES,
            **{
                name: DATA_PRODUCT_AUXILIARY_PROPERTIES
                for name in [
                    "dataobs-data-product-membership-v1",
                    "dataobs-data-product-membership-proposals-v1",
                    "dataobs-data-product-membership-decisions-v1",
                    "dataobs-data-product-slos-v1",
                    "dataobs-data-product-slo-evaluations-v1",
                    "dataobs-data-product-scorecards-v1",
                    "dataobs-data-product-coverage-v1",
                    "dataobs-data-product-impact-current-v1",
                    "dataobs-data-product-dependency-current-v1",
                ]
            },
        },
    },
)

# Resource-specific additions intentionally live in a new migration. 0015 is a
# released migration and its shared auxiliary mapping/checksum must not change.
DATA_PRODUCT_MEMBERSHIP_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "membership_id",
            "tenant_id",
            "environment",
            "product_id",
            "entity_id",
            "entity_type",
            "source",
            "state",
            "proposal_id",
            "evidence_refs",
            "created_by",
            "excluded_by",
            "etag",
            "schema_version",
        ]
    },
    "confidence": {"type": "double"},
    "source_coverage": {"type": "double"},
    **{key: {"type": "date"} for key in ["observed_at", "created_at", "updated_at", "excluded_at"]},
    "exclusion_reason": {"type": "match_only_text"},
    "revision": {"type": "integer"},
}

DATA_PRODUCT_PROPOSAL_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "proposal_id",
            "tenant_id",
            "environment",
            "product_id",
            "entity_id",
            "entity_type",
            "source",
            "state",
            "evidence_refs",
            "missing_inputs",
            "schema_version",
        ]
    },
    "proposal_revision": {"type": "integer"},
    "confidence": {"type": "double"},
    "source_coverage": {"type": "double"},
    "truncated": {"type": "boolean"},
    **{key: {"type": "date"} for key in ["observed_at", "created_at", "updated_at", "expires_at"]},
}

DATA_PRODUCT_DECISION_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "decision_id",
            "operation_id",
            "tenant_id",
            "environment",
            "product_id",
            "proposal_id",
            "membership_id",
            "decision",
            "outcome",
            "actor",
            "request_fingerprint",
            "idempotency_key_hash",
            "result_etag",
            "error_code",
            "schema_version",
        ]
    },
    "reason": {"type": "match_only_text"},
    "expected_revision": {"type": "integer"},
    "result_revision": {"type": "integer"},
    **{key: {"type": "date"} for key in ["decided_at", "occurred_at", "applied_at"]},
}

DATA_PRODUCT_DEPENDENCY_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "tenant_id",
            "environment",
            "product_id",
            "upstream_product_id",
            "relationship",
            "source",
            "evidence_refs",
            "graph_version",
            "schema_version",
        ]
    },
    "confidence": {"type": "double"},
    "product_revision": {"type": "integer"},
    "removed_by_revision": {"type": "integer"},
    "removed": {"type": "boolean"},
    **{key: {"type": "date"} for key in ["observed_at", "created_at", "updated_at", "removed_at"]},
}

DATA_PRODUCT_IMPACT_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "tenant_id",
            "environment",
            "product_id",
            "outputs",
            "active_members",
            "direct_upstream_products",
            "direct_downstream_products",
            "transitive_upstream_products",
            "transitive_downstream_products",
            "pathways",
            "known_consumers",
            "missing_evidence",
            "data_status",
        ]
    },
    "truncated": {"type": "boolean"},
    "source_coverage": {"type": "double"},
    "observed_at": {"type": "date"},
}

DATA_PRODUCT_MEMBERSHIP_DEPENDENCY_RUNTIME_MIGRATION = Migration(
    "0016_data_product_membership_dependency_runtime",
    "Correct strict mappings for the Data Product membership and dependency runtime",
    "v1",
    dependencies=["0015_data_product_360_productization"],
    rollback_strategy="stop membership and dependency writers; retain additive mappings and immutable evidence",
    operations={
        "mapping_updates": {
            "dataobs-data-product-membership-v1": DATA_PRODUCT_MEMBERSHIP_PROPERTIES,
            "dataobs-data-product-membership-proposals-v1": DATA_PRODUCT_PROPOSAL_PROPERTIES,
            "dataobs-data-product-membership-decisions-v1": DATA_PRODUCT_DECISION_PROPERTIES,
            "dataobs-data-product-dependency-current-v1": DATA_PRODUCT_DEPENDENCY_PROPERTIES,
            "dataobs-data-product-impact-current-v1": DATA_PRODUCT_IMPACT_PROPERTIES,
        }
    },
)

# Additive mapping only: released migrations above remain checksum-identical.
DATA_PRODUCT_RECONCILIATION_RETRY_DATE_MIGRATION = Migration(
    "0017_data_product_reconciliation_retry_date",
    "Add a date-safe retry schedule field to Data Product operation state",
    "v1",
    dependencies=["0016_data_product_membership_dependency_runtime"],
    rollback_strategy="stop reconciliation workers; retain the additive date mapping and operation evidence",
    operations={"mapping_updates": {"dataobs-data-product-operation-state-v1": {"next_attempt_at": {"type": "date"}}}},
)

DATA_PRODUCT_DECISION_REASON_ALIAS_MIGRATION = Migration(
    "0018_data_product_decision_reason_alias",
    "Add an additive decision_reason field alongside the existing reason field to avoid mapping collisions",
    "v1",
    dependencies=["0017_data_product_reconciliation_retry_date"],
    rollback_strategy="stop decision writers; retain the additive decision_reason mapping and existing reason field",
    operations={
        "mapping_updates": {
            "dataobs-data-product-membership-decisions-v1": {"decision_reason": {"type": "match_only_text"}}
        }
    },
)

DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION = Migration(
    "0019_data_product_operation_claim_expires_date",
    "Add a date-safe claim expiry field to Data Product operation state",
    "v1",
    dependencies=["0018_data_product_decision_reason_alias"],
    rollback_strategy="stop reconciliation workers; retain the additive date mapping and operation evidence",
    operations={"mapping_updates": {"dataobs-data-product-operation-state-v1": {"claim_expires_at": {"type": "date"}}}},
)

IDENTITY_RBAC_TENANT_BINDINGS_MIGRATION = Migration(
    "0020_identity_rbac_tenant_bindings",
    "Add strict role-binding and security-policy state plus append-only redaction-safe security events",
    "v1",
    dependencies=["0019_data_product_operation_claim_expires_date"],
    rollback_strategy="disable IAM writers; retain additive role bindings and append-only security events for audit continuity",
    operations={
        "mutable_indices": ["dataobs-role-bindings-v1", "dataobs-security-policy-state-v1"],
        "data_streams": ["logs-dataobs.security-event-*"],
    },
)

LINEAGE_ANALYSIS_EXPLORER_MIGRATION = Migration(
    "0021_lineage_analysis_explorer",
    "Add durable dataset/column lineage observations and current analysis projections",
    "v1",
    dependencies=["0020_identity_rbac_tenant_bindings"],
    rollback_strategy="stop lineage projection writers and transforms; retain append-only observations and snapshot current projections before removing only 0021 resources",
    operations={
        "mutable_indices": [
            "dataobs-lineage-current-v1",
            "dataobs-column-lineage-current-v1",
            "dataobs-lineage-analysis-checkpoints-v1",
        ],
        "data_streams": [
            "logs-dataobs.lineage-observation-*",
            "logs-dataobs.column-lineage-observation-*",
        ],
        "transforms": [
            {
                "id": "dataobs-current-dataset-lineage",
                "source": "logs-dataobs.lineage-observation-*",
                "destination": "dataobs-lineage-current-v1",
                "unique_key": ["tenant_id", "environment", "edge_id"],
                "sort": "observed_at",
            },
            {
                "id": "dataobs-current-column-lineage",
                "source": "logs-dataobs.column-lineage-observation-*",
                "destination": "dataobs-column-lineage-current-v1",
                "unique_key": ["tenant_id", "environment", "edge_id"],
                "sort": "observed_at",
            },
        ],
    },
)

AWS_DATA_PLATFORM_COLLECTOR_MIGRATION = Migration(
    "0022_aws_data_platform_collector",
    "Add tenant-scoped provider checkpoints, observations and collection-run evidence",
    "v1",
    dependencies=["0021_lineage_analysis_explorer"],
    rollback_strategy="stop AWS collection writers; retain append-only evidence and checkpoint/run audit state",
    operations={
        "mutable_indices": ["dataobs-provider-checkpoints-v1"],
        "data_streams": ["logs-dataobs.provider-observation-*", "logs-dataobs.collection-run-*"],
    },
)

STREAM_PATHWAY_RELIABILITY_MIGRATION = Migration(
    "0023_stream_pathway_reliability_runtime",
    "Add Team 1 reliability definitions, status, coordination, append-only evaluations and signals",
    "v1",
    dependencies=["0022_aws_data_platform_collector"],
    rollback_strategy="stop Team 1 reliability workers; retain evaluation and signal evidence; snapshot status before removing 0023 aliases and templates",
    operations={
        "mutable_indices": [
            "dataobs-stream-slo-definitions-v1",
            "dataobs-reliability-status-v1",
            "dataobs-reliability-runtime-state-v1",
        ],
        "data_streams": [
            "metrics-dataobs.stream-slo-evaluation-*",
            "metrics-dataobs.pathway-slo-evaluation-*",
            "logs-dataobs.reliability-signal-*",
        ],
        "retention_defaults": {"evaluations": "90d operational evidence", "signals": "365d audit evidence"},
    },
)

JOB_RUN_RELIABILITY_MIGRATION = Migration(
    "0024_job_run_reliability_runtime",
    "Add Team 2 reliability policy, projections, coordination and append-only evaluation evidence",
    "v1",
    dependencies=["0023_stream_pathway_reliability_runtime"],
    rollback_strategy="stop Team 2 reliability workers; retain append-only evaluation evidence; snapshot current policy and runtime state before alias removal",
    operations={
        "mutable_indices": [
            "dataobs-job-reliability-policy-v1",
            "dataobs-job-reliability-current-v1",
            "dataobs-job-reliability-runtime-state-v1",
            "dataobs-expected-run-current-v1",
        ],
        "data_streams": [
            "metrics-dataobs.job-reliability-*",
            "logs-dataobs.expected-run-evaluation-*",
            "logs-dataobs.job-reliability-event-*",
        ],
        "retention_defaults": {"evaluations": "365d append-only evidence"},
    },
)

RELIABILITY_DEFINITION_PROPERTIES = {
    **{
        key: {"type": "keyword", "ignore_above": 512}
        for key in [
            "id",
            "tenant_id",
            "environment",
            "resource_type",
            "resource_id",
            "metric",
            "operator",
            "unit",
            "owner",
            "missing_data_policy",
            "schema_version",
            "created_actor",
            "updated_actor",
            "latest_evaluation_id",
        ]
    },
    **{key: {"type": "boolean"} for key in ["enabled"]},
    "threshold": {"type": "double"},
    **{
        key: {"type": "long"}
        for key in [
            "evaluation_window_seconds",
            "evaluation_interval_seconds",
            "required_consecutive_breaches",
            "recovery_evaluation_count",
            "revision",
        ]
    },
    **{key: {"type": "date"} for key in ["created_at", "updated_at", "next_evaluation_at"]},
}
RELIABILITY_STATUS_PROPERTIES = {
    **{
        key: {"type": "keyword", "ignore_above": 512}
        for key in [
            "status_id",
            "evaluation_id",
            "definition_id",
            "tenant_id",
            "environment",
            "resource_type",
            "resource_id",
            "metric",
            "previous_status",
            "current_status",
            "status",
            "operator",
            "unit",
            "latest_evaluation_id",
            "evidence_type",
            "latency_method",
            "schema_version",
        ]
    },
    **{key: {"type": "double"} for key in ["observed_value", "threshold", "confidence", "source_coverage"]},
    **{
        key: {"type": "long"}
        for key in ["consecutive_breaches", "consecutive_recoveries", "breach_duration_seconds", "revision"]
    },
    **{
        key: {"type": "date"}
        for key in ["first_breach_at", "last_breach_at", "observed_at", "evaluated_at", "transition_at"]
    },
    **{
        key: {"type": "keyword", "ignore_above": 1024}
        for key in ["reason_codes", "warnings", "missing_inputs", "evidence_refs"]
    },
}
RELIABILITY_RUNTIME_PROPERTIES = {
    **{
        key: {"type": "keyword", "ignore_above": 512}
        for key in [
            "scope",
            "tenant_id",
            "environment",
            "worker_id",
            "lease_owner",
            "lease_status",
            "checkpoint_status",
            "elasticsearch_status",
            "runtime_version",
        ]
    },
    "configured": {"type": "boolean"},
    **{
        key: {"type": "date"}
        for key in [
            "expires_at",
            "cycle_started_at",
            "cycle_ended_at",
            "latest_successful_evaluation",
            "latest_failed_evaluation",
            "heartbeat_at",
            "updated_at",
        ]
    },
    **{
        key: {"type": "long"}
        for key in [
            "fencing_token",
            "definitions_due",
            "definitions_evaluated",
            "definitions_skipped",
            "definitions_failed",
            "consecutive_failures",
            "pending_reconciliation_count",
            "pending_signal_count",
        ]
    },
}

STREAM_PATHWAY_RELIABILITY_PRODUCTION_CLOSURE_MIGRATION = Migration(
    "0025_stream_pathway_reliability_production_closure",
    "Install strict reliability mappings and retained append-only stream contracts",
    "v1",
    dependencies=["0024_job_run_reliability_runtime"],
    rollback_strategy="stop reliability workers; retain append-only evaluation and signal evidence; restore mutable indices from snapshot; templates and lifecycle policies may be removed only after retention review",
    operations={
        "mapping_updates": {
            "dataobs-stream-slo-definitions-v1": RELIABILITY_DEFINITION_PROPERTIES,
            "dataobs-reliability-status-v1": RELIABILITY_STATUS_PROPERTIES,
            "dataobs-reliability-runtime-state-v1": RELIABILITY_RUNTIME_PROPERTIES,
        },
        "data_stream_contracts": {
            "metrics-dataobs.stream-slo-evaluation-*": {
                "retention": "90d",
                "properties": RELIABILITY_STATUS_PROPERTIES | {"@timestamp": {"type": "date"}},
            },
            "metrics-dataobs.pathway-slo-evaluation-*": {
                "retention": "90d",
                "properties": RELIABILITY_STATUS_PROPERTIES | {"@timestamp": {"type": "date"}},
            },
            "logs-dataobs.reliability-signal-*": {
                "retention": "365d",
                "properties": RELIABILITY_STATUS_PROPERTIES
                | {
                    "signal_id": {"type": "keyword"},
                    "severity": {"type": "keyword"},
                    "transition_at": {"type": "date"},
                    "@timestamp": {"type": "date"},
                },
            },
        },
    },
)

STREAM_INTELLIGENCE_PROPERTIES = {
    **{
        key: {"type": "keyword", "ignore_above": 1024}
        for key in [
            "id",
            "detector_id",
            "candidate_id",
            "forecast_id",
            "evaluation_id",
            "tenant_id",
            "environment",
            "resource_type",
            "resource_id",
            "metric",
            "method",
            "direction",
            "state",
            "previous_state",
            "owner",
            "classification",
            "schema_version",
            "created_actor",
            "updated_actor",
            "worker_id",
            "lease_status",
            "error_fingerprint",
            "reason_codes",
            "missing_inputs",
            "evidence_references",
            "overlay_references",
        ]
    },
    **{
        key: {"type": "double"}
        for key in [
            "observed_value",
            "expected_value",
            "range_lower",
            "range_upper",
            "deviation_score",
            "data_coverage",
            "confidence",
            "current_lag",
            "current_backlog_age_seconds",
            "current_backlog_bytes",
            "production_rate",
            "consumption_rate",
            "net_backlog_growth_rate",
            "estimated_drain_time_seconds",
            "earliest_exhaustion_seconds",
        ]
    },
    **{
        key: {"type": "long"}
        for key in [
            "revision",
            "sample_count",
            "consecutive_anomalies",
            "consecutive_recoveries",
            "fencing_token",
            "partition",
        ]
    },
    **{key: {"type": "boolean"} for key in ["enabled", "configured"]},
    **{
        key: {"type": "date"}
        for key in [
            "@timestamp",
            "created_at",
            "updated_at",
            "observed_at",
            "evaluated_at",
            "next_evaluation_at",
            "heartbeat_at",
        ]
    },
}

STREAM_ANOMALY_RETENTION_INTELLIGENCE_MIGRATION = Migration(
    "0026_stream_anomaly_retention_intelligence",
    "Add strict Team 1 anomaly, retention forecast and metadata-only failure intelligence storage",
    "v1",
    dependencies=["0025_stream_pathway_reliability_production_closure"],
    rollback_strategy="stop intelligence workers; retain append-only evidence and signals; snapshot current projections before alias removal",
    operations={
        "mutable_indices": [
            "dataobs-stream-detector-definitions-v1",
            "dataobs-stream-anomaly-current-v1",
            "dataobs-stream-retention-forecast-current-v1",
            "dataobs-stream-failure-candidate-current-v1",
            "dataobs-stream-intelligence-runtime-state-v1",
        ],
        "mapping_updates": {
            name: STREAM_INTELLIGENCE_PROPERTIES
            for name in [
                "dataobs-stream-detector-definitions-v1",
                "dataobs-stream-anomaly-current-v1",
                "dataobs-stream-retention-forecast-current-v1",
                "dataobs-stream-failure-candidate-current-v1",
                "dataobs-stream-intelligence-runtime-state-v1",
            ]
        },
        "data_stream_contracts": {
            "metrics-dataobs.stream-anomaly-evaluation-*": {
                "retention": "90d",
                "properties": STREAM_INTELLIGENCE_PROPERTIES,
            },
            "metrics-dataobs.stream-retention-forecast-*": {
                "retention": "90d",
                "properties": STREAM_INTELLIGENCE_PROPERTIES,
            },
            "logs-dataobs.stream-failure-candidate-*": {
                "retention": "180d",
                "properties": STREAM_INTELLIGENCE_PROPERTIES,
            },
            "logs-dataobs.stream-intelligence-signal-*": {
                "retention": "365d",
                "properties": STREAM_INTELLIGENCE_PROPERTIES,
            },
        },
    },
)

PLATFORM_LIFECYCLE_PROPERTIES = {
    **{
        key: {"type": "keyword"}
        for key in [
            "resource_id",
            "resource_type",
            "platform_owner",
            "state",
            "reason_code",
            "actor",
            "created_actor",
            "updated_actor",
            "etag",
            "schema_version",
            "environment_id",
            "cluster_id",
            "installation_id",
            "tenant_id",
            "release_sha",
            "chart_version",
            "terminal_migration",
            "desired_state_hash",
            "observed_state_hash",
            "drift_state",
            "idempotency_key",
        ]
    },
    **{key: {"type": "date"} for key in ["created_at", "updated_at", "timestamp"]},
    "revision": {"type": "long"},
    "metadata": {"type": "flattened"},
}

PLATFORM_LIFECYCLE_MIGRATION = Migration(
    "0027_platform_environment_tenant_multicluster_lifecycle",
    "Add strict metadata-only platform lifecycle projections and append-only evidence",
    "v1",
    dependencies=["0026_stream_anomaly_retention_intelligence"],
    rollback_strategy="stop lifecycle writers; retain append-only evidence and snapshots; never reverse tenant deletion or Elasticsearch data migrations",
    operations={
        "mutable_indices": [
            "dataobs-platform-environments-v1",
            "dataobs-platform-clusters-v1",
            "dataobs-platform-installations-v1",
            "dataobs-platform-deployment-plans-v1",
            "dataobs-platform-tenant-lifecycle-v1",
            "dataobs-platform-lifecycle-operations-v1",
        ],
        "mapping_updates": {
            name: PLATFORM_LIFECYCLE_PROPERTIES
            for name in [
                "dataobs-platform-environments-v1",
                "dataobs-platform-clusters-v1",
                "dataobs-platform-installations-v1",
                "dataobs-platform-deployment-plans-v1",
                "dataobs-platform-tenant-lifecycle-v1",
                "dataobs-platform-lifecycle-operations-v1",
            ]
        },
        "data_stream_contracts": {
            "logs-dataobs.platform-lifecycle-evidence-*": {
                "retention": "2555d",
                "properties": PLATFORM_LIFECYCLE_PROPERTIES,
            }
        },
    },
)

PATHWAY_INVESTIGATION_PROPERTIES = {
    **{
        key: {"type": "keyword"}
        for key in [
            "snapshot_id",
            "tenant_id",
            "environment",
            "pathway_id",
            "graph_hash",
            "classification",
            "schema_version",
            "node_ids",
            "edge_ids",
            "change_reason_codes",
            "source_coverage",
            "missing_inputs",
            "evidence_refs",
        ]
    },
    **{key: {"type": "date"} for key in ["effective_at", "observed_at"]},
    **{key: {"type": "integer"} for key in ["node_count", "edge_count"]},
    "confidence": {"type": "double"},
    "nodes": {
        "type": "nested",
        "dynamic": "strict",
        "properties": {
            "node_id": {"type": "keyword"},
            "node_type": {"type": "keyword"},
            "display_name": {"type": "keyword"},
            "confidence": {"type": "double"},
            "source_coverage": {"type": "keyword"},
            "evidence_refs": {"type": "keyword"},
            "data_status": {"type": "keyword"},
        },
    },
    "edges": {
        "type": "nested",
        "dynamic": "strict",
        "properties": {
            "edge_id": {"type": "keyword"},
            "source_node_id": {"type": "keyword"},
            "destination_node_id": {"type": "keyword"},
            "relationship": {"type": "keyword"},
            "topic": {"type": "keyword"},
            "consumer_group": {"type": "keyword"},
            "confidence": {"type": "double"},
            "source_coverage": {"type": "keyword"},
            "evidence_refs": {"type": "keyword"},
            "data_status": {"type": "keyword"},
        },
    },
}

PATHWAY_INVESTIGATION_HISTORY_MIGRATION = Migration(
    "0028_pathway_investigation_history",
    "Add strict forward-only pathway topology snapshots and fenced history state",
    "v1",
    dependencies=["0027_platform_environment_tenant_multicluster_lifecycle"],
    rollback_strategy="stop history projector; retain append-only snapshots; remove write aliases only after export",
    operations={
        "mutable_indices": ["dataobs-pathway-history-state-v1"],
        "mapping_updates": {
            "dataobs-pathway-history-state-v1": {
                **{
                    key: {"type": "keyword"}
                    for key in [
                        "tenant_id",
                        "environment",
                        "pathway_id",
                        "graph_hash",
                        "checkpoint",
                        "lease_owner",
                        "schema_version",
                    ]
                },
                **{key: {"type": "date"} for key in ["last_snapshot_at", "latest_source_at", "lease_expires_at"]},
                "fencing_token": {"type": "long"},
            }
        },
        "data_stream_contracts": {
            "logs-dataobs.pathway-topology-snapshot-*": {
                "retention": "365d",
                "properties": PATHWAY_INVESTIGATION_PROPERTIES,
            }
        },
    },
)


TEAM2_DATA_INTELLIGENCE_PROPERTIES: Dict[str, Any] = {
    **BASE_PROPERTIES,
    **{
        key: {"type": "keyword"}
        for key in [
            "contract_id",
            "revision_id",
            "canonical_asset_identity",
            "owner",
            "lifecycle_state",
            "enforcement_mode",
            "criticality",
            "fingerprint",
            "evaluation_id",
            "requirement_id",
            "category",
            "severity",
            "directness",
            "reason_code",
            "actor",
            "source",
            "data_status",
            "change_id",
            "impact_id",
            "change_type",
            "compatibility",
            "asset_kind",
            "entity_type",
            "entity_id",
            "lease_owner",
            "checkpoint",
            "health_state",
        ]
    },
    **{
        key: {"type": "date"}
        for key in [
            "effective_from",
            "effective_until",
            "evaluated_at",
            "observation_time",
            "detected_at",
            "lease_expires_at",
            "heartbeat_at",
        ]
    },
    "contract_version": {"type": "integer"},
    "revision": {"type": "long"},
    "fencing_token": {"type": "long"},
    "depth": {"type": "integer"},
    "confidence": {"type": "float"},
    "score": {"type": "float"},
    "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
    "description": {"type": "text"},
    "tags": {"type": "keyword"},
    "data_product_ids": {"type": "keyword"},
    "affected_asset_ids": {"type": "keyword"},
    "affected_job_ids": {"type": "keyword"},
    "affected_monitor_ids": {"type": "keyword"},
    "affected_owner_ids": {"type": "keyword"},
    "incident_references": {"type": "keyword"},
    "evidence_references": {"type": "keyword"},
    "policy": {"type": "flattened"},
    "expected": {"type": "flattened"},
    "observed": {"type": "flattened"},
    "approval_evidence": {"type": "flattened"},
    "paths": {"type": "flattened"},
}

TEAM2_DATA_INTELLIGENCE_RECONCILIATION_MIGRATION = Migration(
    "0029_team2_data_intelligence_reconciliation",
    "Restore Team 2 lineage intelligence and Data Contract storage lost in parallel merges",
    "v1",
    dependencies=["0028_pathway_investigation_history"],
    rollback_strategy=(
        "stop Team 2 writers; export projections and retain append-only governance, "
        "change, impact, evaluation, and violation evidence"
    ),
    operations={
        "mutable_indices": [
            "dataobs-lineage-impact-current-v1",
            "dataobs-lineage-change-current-v1",
            "dataobs-lineage-runtime-state-v1",
            "dataobs-data-contract-current-v1",
            "dataobs-data-contract-health-current-v1",
            "dataobs-data-contract-runtime-state-v1",
        ],
        "mapping_updates": {
            name: TEAM2_DATA_INTELLIGENCE_PROPERTIES
            for name in [
                "dataobs-lineage-impact-current-v1",
                "dataobs-lineage-change-current-v1",
                "dataobs-lineage-runtime-state-v1",
                "dataobs-data-contract-current-v1",
                "dataobs-data-contract-health-current-v1",
                "dataobs-data-contract-runtime-state-v1",
            ]
        },
        "data_stream_contracts": {
            name: {"retention": retention, "properties": TEAM2_DATA_INTELLIGENCE_PROPERTIES}
            for name, retention in {
                "logs-dataobs.lineage-change-*": "365d",
                "logs-dataobs.lineage-impact-evaluation-*": "365d",
                "logs-dataobs.data-contract-version-*": "3650d",
                "logs-dataobs.data-contract-lifecycle-*": "3650d",
                "logs-dataobs.data-contract-evaluation-*": "365d",
                "logs-dataobs.data-contract-violation-*": "730d",
            }.items()
        },
    },
)


MESSAGING_RUNTIME_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "tenant_id",
            "environment",
            "messaging_system",
            "provider",
            "provider_account_scope",
            "cloud",
            "region_or_location",
            "resource_kind",
            "resource_id",
            "provider_resource_id",
            "namespace_id",
            "parent_resource_id",
            "subscription_id",
            "consumer_group_id",
            "partition_id",
            "shard_id",
            "dead_letter_resource_id",
            "data_status",
            "measurement_method",
            "collection_method",
            "source_integration",
            "schema_version",
            "metric_family",
            "lease_status",
            "collection_state",
            "projection_state",
            "latest_error_code",
            "checkpoint_scope",
            "source_watermark",
        ]
    },
    **{
        key: {"type": "date"}
        for key in [
            "observed_at",
            "ingested_at",
            "last_observation_at",
            "last_projection_at",
            "heartbeat_at",
            "last_successful_cycle",
            "next_retry",
            "latest_source_timestamp",
        ]
    },
    **{
        key: {"type": "long"}
        for key in [
            "fencing_token",
            "failure_count",
            "observations_read",
            "observations_normalized",
            "observations_rejected",
            "projections_updated",
            "stale_resource_count",
            "partial_resource_count",
            "pending_reconciliation_count",
            "consecutive_failures",
        ]
    },
    **{key: {"type": "double"} for key in ["confidence", "source_coverage", "value"]},
    "configured": {"type": "boolean"},
    "missing_inputs": {"type": "keyword"},
    "continuation_token": {"type": "keyword", "index": False},
    "provider_facets": {"type": "flattened"},
}

TEAM1_MULTI_BROKER_MESSAGING_RUNTIME_MIGRATION = Migration(
    "0030_team1_multi_broker_messaging_runtime",
    "Add strict provider-neutral messaging evidence, current projections, checkpoints, and runtime state",
    "v1",
    dependencies=["0029_team2_data_intelligence_reconciliation"],
    rollback_strategy="stop messaging projection writers; retain append-only evidence and additive projections",
    operations={
        "mutable_indices": [
            "dataobs-messaging-resources-v1",
            "dataobs-messaging-backlog-current-v1",
            "dataobs-messaging-throughput-current-v1",
            "dataobs-messaging-delivery-current-v1",
            "dataobs-messaging-dead-letter-current-v1",
            "dataobs-messaging-runtime-state-v1",
            "dataobs-messaging-checkpoints-v1",
        ],
        "mapping_updates": {
            name: MESSAGING_RUNTIME_PROPERTIES
            for name in [
                "dataobs-messaging-resources-v1",
                "dataobs-messaging-backlog-current-v1",
                "dataobs-messaging-throughput-current-v1",
                "dataobs-messaging-delivery-current-v1",
                "dataobs-messaging-dead-letter-current-v1",
                "dataobs-messaging-runtime-state-v1",
                "dataobs-messaging-checkpoints-v1",
            ]
        },
        "data_stream_contracts": {
            name: {"retention": "365d", "properties": MESSAGING_RUNTIME_PROPERTIES}
            for name in [
                "metrics-dataobs.messaging-resource-*",
                "metrics-dataobs.messaging-backlog-*",
                "metrics-dataobs.messaging-throughput-*",
                "metrics-dataobs.messaging-delivery-*",
                "logs-dataobs.messaging-resource-event-*",
                "logs-dataobs.messaging-dead-letter-event-*",
            ]
        },
    },
)


POST_INCIDENT_REVIEW_ANALYTICS_MIGRATION = Migration(
    "0031_team3_post_incident_review_analytics",
    "Add strict post-incident review, follow-up, event, and per-incident analytics resources",
    "v1",
    dependencies=["0030_team1_multi_broker_messaging_runtime"],
    rollback_strategy="stop Team 3 writers; retain immutable review and follow-up audit evidence",
    operations={
        "mutable_indices": [
            "dataobs-incident-reviews-current-v1",
            "dataobs-incident-followups-current-v1",
            "dataobs-incident-analytics-current-v1",
        ],
        "mapping_updates": {
            "dataobs-incident-reviews-current-v1": {
                "dynamic": "strict",
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "review_id": {"type": "keyword"},
                    "incident_id": {"type": "keyword"},
                    "review_generation": {"type": "integer"},
                    "review_status": {"type": "keyword"},
                    "requirement_state": {"type": "keyword"},
                    "owner": {"type": "keyword"},
                    "due_at": {"type": "date"},
                    "completed_at": {"type": "date"},
                    "incident_revision": {"type": "keyword"},
                    "evidence_cutoff": {"type": "date"},
                    "policy_id": {"type": "keyword"},
                    "policy_version": {"type": "keyword"},
                    "policy_hash": {"type": "keyword"},
                    "sections": {"type": "object", "enabled": False},
                },
            },
            "dataobs-incident-followups-current-v1": {
                "dynamic": "strict",
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "followup_id": {"type": "keyword"},
                    "incident_id": {"type": "keyword"},
                    "review_id": {"type": "keyword"},
                    "followup_status": {"type": "keyword"},
                    "followup_category": {"type": "keyword"},
                    "priority": {"type": "keyword"},
                    "owner": {"type": "keyword"},
                    "due_at": {"type": "date"},
                    "completed_at": {"type": "date"},
                },
            },
            "dataobs-incident-analytics-current-v1": {
                "dynamic": "strict",
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "incident_id": {"type": "keyword"},
                    "opened_at": {"type": "date"},
                    "severity": {"type": "keyword"},
                    "priority": {"type": "keyword"},
                    "time_to_acknowledge_ms": {"type": "long"},
                    "time_to_resolve_ms": {"type": "long"},
                    "time_to_close_ms": {"type": "long"},
                    "signal_to_incident_ms": {"type": "long"},
                    "waiting_for_approval_duration_ms": {"type": "long"},
                    "monitoring_recovery_duration_ms": {"type": "long"},
                    "reopen_count": {"type": "integer"},
                    "was_reopened": {"type": "boolean"},
                    "source_incident_revision": {"type": "keyword"},
                    "source_timeline_checkpoint": {"type": "keyword"},
                    "metric_definition_version": {"type": "keyword"},
                    "projection_version": {"type": "integer"},
                    "computed_at": {"type": "date"},
                },
            },
        },
        "data_stream_contracts": {
            "logs-dataobs.incident-review-event-*": {
                "retention": "2555d",
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "incident_id": {"type": "keyword"},
                    "review_id": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "@timestamp": {"type": "date"},
                },
            },
            "logs-dataobs.incident-followup-event-*": {
                "retention": "2555d",
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "incident_id": {"type": "keyword"},
                    "followup_id": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "@timestamp": {"type": "date"},
                },
            },
        },
    },
)

DATA_SLO_PROPERTIES: Dict[str, Any] = {
    **{
        key: {"type": "keyword"}
        for key in [
            "slo_id",
            "tenant_id",
            "environment",
            "scope_type",
            "scope_id",
            "name",
            "description",
            "sli_type",
            "window",
            "window_type",
            "evaluation_granularity",
            "missing_evidence_policy",
            "criticality",
            "owner_team",
            "state",
            "etag",
            "created_by",
            "updated_by",
            "schema_version",
            "evaluation_id",
            "burn_classification",
            "evidence_status",
            "evaluation_method_version",
            "lease_owner",
            "worker_id",
        ]
    },
    **{
        key: {"type": "date"}
        for key in [
            "created_at",
            "updated_at",
            "window_start",
            "window_end",
            "evaluated_at",
            "last_evaluated",
            "next_evaluation_at",
            "lease_expires_at",
            "last_checkpoint",
            "last_success",
            "last_failure",
            "estimated_exhaustion_at",
        ]
    },
    **{
        key: {"type": "integer"}
        for key in [
            "revision",
            "definition_revision",
            "expected_intervals",
            "eligible_intervals",
            "good_intervals",
            "bad_intervals",
            "unknown_intervals",
            "excluded_intervals",
            "attempt_count",
        ]
    },
    **{key: {"type": "long"} for key in ["fencing_token"]},
    **{
        key: {"type": "double"}
        for key in [
            "objective",
            "sli_actual",
            "current_sli",
            "coverage_ratio",
            "coverage",
            "confidence",
            "budget_total",
            "budget_consumed",
            "budget_remaining",
            "short_window_burn",
            "long_window_burn",
            "short_burn_rate",
            "long_burn_rate",
            "forecast_confidence",
        ]
    },
    "source_monitor_ids": {"type": "keyword"},
    "source_job_ids": {"type": "keyword"},
    "source_contract_ids": {"type": "keyword"},
    "evidence_refs": {"type": "keyword", "index": False},
    "reason_codes": {"type": "keyword"},
    "definition": {"type": "object", "enabled": False},
    "downstream_impact_summary": {"type": "object", "enabled": False},
}

TEAM2_DATA_SLO_PRODUCTION_RUNTIME_MIGRATION = Migration(
    "0032_team2_data_slo_production_runtime",
    "Persist canonical SLO definitions, immutable evaluations, projections, and fenced runtime",
    "v1",
    dependencies=["0031_team3_post_incident_review_analytics"],
    rollback_strategy="stop SLO workers; retain immutable evaluations and definition audit history",
    operations={
        "mutable_indices": [
            "dataobs-slo-definition-current-v1",
            "dataobs-slo-current-v1",
            "dataobs-slo-runtime-state-v1",
        ],
        "mapping_updates": {
            name: {"dynamic": "strict", "properties": DATA_SLO_PROPERTIES}
            for name in ["dataobs-slo-definition-current-v1", "dataobs-slo-current-v1", "dataobs-slo-runtime-state-v1"]
        },
        "data_stream_contracts": {
            name: {"retention": retention, "properties": DATA_SLO_PROPERTIES}
            for name, retention in {
                "logs-dataobs.slo-definition-event-*": "3650d",
                "logs-dataobs.slo-evaluation-*": "730d",
            }.items()
        },
    },
)


SCHEMA_INTELLIGENCE_PROPERTIES = {
    "dynamic": "strict",
    "properties": {
        **{
            key: {"type": "keyword"}
            for key in [
                "event_id",
                "tenant_id",
                "environment",
                "integration_id",
                "registry_id",
                "subject_id",
                "subject_fingerprint",
                "schema_id",
                "schema_type",
                "schema_fingerprint",
                "compatibility_mode",
                "structural_fingerprint",
                "data_status",
                "measurement_method",
                "schema_version_contract",
                "evaluation_method",
                "policy",
                "result",
                "compatibility_result",
                "technical_severity",
                "resource_id",
                "messaging_system",
                "binding_method",
                "consumer_id",
                "consumer_group_or_subscription",
                "exposure_state",
                "compatibility_state",
                "worker_id",
                "checkpoint",
                "collection_state",
                "projection_state",
                "lease_status",
                "latest_error_code",
                "latest_compatibility",
                "application_id",
                "role",
            ]
        },
        **{
            key: {"type": "date"}
            for key in ["observed_at", "ingested_at", "evaluated_at", "heartbeat_at", "lease_expiry"]
        },
        **{
            key: {"type": "long"}
            for key in [
                "schema_version",
                "latest_version",
                "reference_count",
                "field_count",
                "schema_error_count",
                "fencing_token",
                "subjects_seen",
                "versions_seen",
                "changes_detected",
                "compatible_count",
                "incompatible_count",
                "unknown_count",
                "potentially_exposed_consumers",
                "incompatible_consumers",
                "degraded_consumers",
                "pending_reconciliations",
            ]
        },
        "known_supported_versions": {"type": "long"},
        **{key: {"type": "double"} for key in ["confidence", "source_coverage", "binding_confidence"]},
        **{key: {"type": "boolean"} for key in ["authoritative", "configured"]},
        **{
            key: {"type": "keyword"}
            for key in [
                "limitations",
                "evidence_refs",
                "change_categories",
                "field_hashes",
                "missing_inputs",
                "reason_codes",
            ]
        },
        "change_counts": {"type": "flattened"},
    },
}

TEAM1_STREAM_SCHEMA_INTELLIGENCE_RUNTIME_MIGRATION = Migration(
    "0033_team1_stream_schema_intelligence_runtime",
    "Add privacy-safe schema evidence, OCC projections, bindings, impacts, and fenced runtime state",
    "v1",
    dependencies=["0032_team2_data_slo_production_runtime"],
    rollback_strategy="stop schema intelligence writers; retain append-only derived evidence",
    operations={
        "mutable_indices": [
            "dataobs-stream-schema-subject-current-v1",
            "dataobs-stream-schema-version-current-v1",
            "dataobs-stream-schema-binding-current-v1",
            "dataobs-stream-schema-impact-current-v1",
            "dataobs-stream-schema-runtime-state-v1",
        ],
        "mapping_updates": {
            name: SCHEMA_INTELLIGENCE_PROPERTIES
            for name in [
                "dataobs-stream-schema-subject-current-v1",
                "dataobs-stream-schema-version-current-v1",
                "dataobs-stream-schema-binding-current-v1",
                "dataobs-stream-schema-impact-current-v1",
                "dataobs-stream-schema-runtime-state-v1",
            ]
        },
        "data_stream_contracts": {
            name: {"retention": "365d", "properties": SCHEMA_INTELLIGENCE_PROPERTIES["properties"]}
            for name in [
                "logs-dataobs.stream-schema-version-*",
                "logs-dataobs.stream-schema-change-*",
                "logs-dataobs.stream-schema-compatibility-*",
                "logs-dataobs.stream-schema-consumer-impact-*",
            ]
        },
    },
)


def migrations() -> List[Migration]:
    return [
        FOUNDATION_MIGRATION,
        POSTGRES_OBSERVABILITY_MIGRATION,
        INCIDENT_AUTOMATION_MIGRATION,
        KAFKA_DSM_MIGRATION,
        CONSOLE_FOUNDATION_MIGRATION,
        PATHWAY_ASSET_360_MIGRATION,
        AUTOMATED_MONITORING_MIGRATION,
        JOB_RUN_OBSERVABILITY_MIGRATION,
        TOPIC_QUEUE_STREAM_360_MIGRATION,
        TOPIC_QUEUE_STREAM_360_COMPLETION_MIGRATION,
        INCIDENT_AUTOMATION_WORKBENCH_MIGRATION,
        INCIDENT_MAPPING_AND_OCC_FIX_MIGRATION,
        MONITOR_RUNTIME_COMPLETION_MIGRATION,
        DATA_PRODUCT_360_COMPLETION_MIGRATION,
        DATA_PRODUCT_360_PRODUCTIZATION_MIGRATION,
        DATA_PRODUCT_MEMBERSHIP_DEPENDENCY_RUNTIME_MIGRATION,
        DATA_PRODUCT_RECONCILIATION_RETRY_DATE_MIGRATION,
        DATA_PRODUCT_DECISION_REASON_ALIAS_MIGRATION,
        DATA_PRODUCT_CLAIM_EXPIRES_DATE_MIGRATION,
        IDENTITY_RBAC_TENANT_BINDINGS_MIGRATION,
        LINEAGE_ANALYSIS_EXPLORER_MIGRATION,
        AWS_DATA_PLATFORM_COLLECTOR_MIGRATION,
        STREAM_PATHWAY_RELIABILITY_MIGRATION,
        JOB_RUN_RELIABILITY_MIGRATION,
        STREAM_PATHWAY_RELIABILITY_PRODUCTION_CLOSURE_MIGRATION,
        STREAM_ANOMALY_RETENTION_INTELLIGENCE_MIGRATION,
        PLATFORM_LIFECYCLE_MIGRATION,
        PATHWAY_INVESTIGATION_HISTORY_MIGRATION,
        TEAM2_DATA_INTELLIGENCE_RECONCILIATION_MIGRATION,
        TEAM1_MULTI_BROKER_MESSAGING_RUNTIME_MIGRATION,
        POST_INCIDENT_REVIEW_ANALYTICS_MIGRATION,
        TEAM2_DATA_SLO_PRODUCTION_RUNTIME_MIGRATION,
        TEAM1_STREAM_SCHEMA_INTELLIGENCE_RUNTIME_MIGRATION,
    ]


def registered_mutable_resources() -> tuple[str, ...]:
    """Exact concrete indices a guarded certification reset may remove."""
    resources = {MIGRATION_STATE_INDEX}
    for migration in migrations():
        resources.update(migration.operations.get("mutable_indices", ()))
        resources.update(migration.operations.get("mapping_updates", {}))
    if any("*" in resource or "?" in resource for resource in resources):
        raise RuntimeError("mutable migration resource registry must contain no wildcards")
    return tuple(sorted(resources))
