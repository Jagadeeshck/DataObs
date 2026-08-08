from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CaseProviderState(StrEnum):
    AVAILABLE = "available"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    FORBIDDEN = "forbidden"
    UNREACHABLE = "unreachable"
    UNSUPPORTED = "unsupported_version"


class CaseLinkState(StrEnum):
    UNLINKED = "unlinked"
    CREATE_RESERVED = "create_reserved"
    CREATE_SUBMITTED = "create_submitted"
    CREATE_RECONCILIATION_REQUIRED = "create_reconciliation_required"
    LINKED = "linked"
    SYNC_REQUIRED = "sync_required"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"
    REMOTE_MISSING = "remote_missing"


class CaseLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link_id: str
    tenant_id: str
    environment: str
    incident_id: str
    kibana_space: str
    reconciliation_reference: str
    creation_actor: str
    request_id: str
    state: CaseLinkState = CaseLinkState.UNLINKED
    elastic_case_id: str | None = None
    elastic_case_version: str | None = None
    owner: str = "observability"
    case_status: str | None = None
    case_severity: str | None = None
    assignees: tuple[str, ...] = ()
    sync_state: str = "pending"
    last_successful_sync: datetime | None = None
    last_attempted_sync: datetime | None = None
    last_observed_remote_update: datetime | None = None
    revision: int = Field(default=0, ge=0)
