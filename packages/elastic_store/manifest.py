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


def migrations() -> List[Migration]:
    return [FOUNDATION_MIGRATION, POSTGRES_OBSERVABILITY_MIGRATION]
