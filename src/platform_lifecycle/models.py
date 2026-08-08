from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_id(value: str, field_name: str = "identifier") -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} must match {IDENTIFIER.pattern}")
    return value


def state_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class EnvironmentState(StrEnum):
    REQUESTED = "requested"
    PROVISIONING = "provisioning"
    CONFIGURED = "configured"
    VALIDATING = "validating"
    READY = "ready"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UPGRADE_PENDING = "upgrade_pending"
    UPGRADING = "upgrading"
    ROLLBACK_PENDING = "rollback_pending"
    RETIRING = "retiring"
    RETIRED = "retired"
    FAILED = "failed"


class ClusterState(StrEnum):
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    VALIDATING = "validating"
    READY = "ready"
    DEGRADED = "degraded"
    DRAINING = "draining"
    UNREGISTERED = "unregistered"


class InstallationState(StrEnum):
    PLANNED = "planned"
    INSTALLING = "installing"
    MIGRATING = "migrating"
    VALIDATING = "validating"
    ACTIVE = "active"
    UPGRADING = "upgrading"
    ROLLING_BACK = "rolling_back"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    REMOVING = "removing"
    REMOVED = "removed"


class TenantState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PROVISIONING = "provisioning"
    VALIDATING = "validating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    OFFBOARDING = "offboarding"
    RETENTION_HOLD = "retention_hold"
    DELETING = "deleting"
    DELETED = "deleted"
    FAILED = "failed"


@dataclass
class Record:
    id: str
    state: str
    created_actor: str
    updated_actor: str
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    revision: int = 1
    schema_version: str = "1"
    reason_code: str = "requested"

    @property
    def etag(self) -> str:
        return f'W/"{self.revision}"'

    def document(self) -> dict[str, Any]:
        result = asdict(self)
        result["etag"] = self.etag
        return result


@dataclass
class Environment(Record):
    name: str = ""
    environment_class: str = "development"
    region: str = ""
    provider: str = "other"
    cluster_id: str | None = None
    installation_id: str | None = None
    elasticsearch_connection_reference: str = ""
    oidc_configuration_reference: str = ""
    telemetry_configuration_reference: str = ""
    secret_provider_type: str = "external"
    release_version: str = ""
    release_sha: str = ""
    chart_version: str = ""
    image_digests: dict[str, str] = field(default_factory=dict)
    terminal_migration: str = ""
    support_matrix_profile: str = "unvalidated"
    tenancy_profile: str = "shared"
    ha_profile: str = "development"
    dr_profile: dict[str, Any] = field(default_factory=dict)
    backup_profile: str = "default"
    capacity_profile: str = "small"
    configuration_revision: str = ""
    desired_state_hash: str = ""
    observed_state_hash: str = ""
    drift_state: str = "unknown"


@dataclass
class Cluster(Record):
    provider: str = "other"
    region: str = ""
    kubernetes_version: str = ""
    architecture: str = "amd64"
    environment_classification: str = "development"
    capacity_class: str = "small"
    availability_zones: list[str] = field(default_factory=list)
    network_profile: str = "private"
    ingress_class: str = ""
    storage_class: str = ""
    secret_provider: str = "external"
    telemetry_endpoint_reference: str = ""
    supported_profile: str = "unvalidated"
    maintenance_state: str = "available"
    health: str = "unknown"
    drift: str = "unknown"


@dataclass
class Installation(Record):
    cluster_id: str = ""
    namespace: str = ""
    helm_release_name: str = ""
    environment_id: str = ""
    release_sha: str = ""
    candidate_version: str = ""
    chart_version: str = ""
    image_digests: dict[str, str] = field(default_factory=dict)
    terminal_migration: str = ""
    elasticsearch_target_fingerprint: str = ""
    oidc_issuer_identifier: str = ""
    tenant_count: int = 0
    desired_replicas: dict[str, int] = field(default_factory=dict)
    observed_replicas: dict[str, int] = field(default_factory=dict)
    desired_state_hash: str = ""
    observed_state_hash: str = ""
    readiness_state: str = "unknown"
    last_upgrade: str | None = None
    last_rollback: str | None = None
    last_certification: str | None = None


@dataclass
class Tenant(Record):
    name: str = ""
    owner: str = ""
    business_reference: str = ""
    allowed_environments: list[str] = field(default_factory=list)
    region_requirements: list[str] = field(default_factory=list)
    residency: str = ""
    data_classification: str = "internal"
    retention_profile: str = "default"
    capacity_profile: str = "small"
    integration_profile: str = "default"
    requested_environment: str = ""
    change_reference: str = ""
    isolation_profile: str = "shared"
    initial_administrators: list[str] = field(default_factory=list)
    installation_id: str | None = None
    backup_verified: bool = False
    retention_hold: bool = False
    deletion_approved_by: str | None = None
    offboarding_phase: str | None = None


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    resource_type: str
    resource_id: str
    event_type: str
    from_state: str | None
    to_state: str
    actor: str
    permission: str
    reason_code: str
    idempotency_key: str
    revision: int
    timestamp: str
