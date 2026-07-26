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
    "decision_reason": {"type": "match_only_text"},
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
