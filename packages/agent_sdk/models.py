from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Any

class Status(str, Enum):
    success="success"; partial="partial"; failed="failed"; timeout="timeout"
class ErrorCategory(str, Enum):
    none="none"; auth="auth"; network="network"; timeout="timeout"; permission="permission"; validation="validation"; connector="connector"; unknown="unknown"
@dataclass(frozen=True)
class ConnectorIdentity:
    name: str; version: str; source_system: str
@dataclass(frozen=True)
class ConnectorCapabilities:
    discovery: bool=True; schema_snapshot: bool=True; freshness: bool=False; profiling: bool=False; quality: bool=False; lineage: bool=False; query_history: bool=False; supports_read_only: bool=True; emits_raw_rows: bool=False
@dataclass(frozen=True)
class SecretReference:
    provider: str; key: str; field: str|None=None
    def __repr__(self): return f"SecretReference(provider={self.provider!r}, key=***REDACTED***, field=***REDACTED***)"
    __str__=__repr__
@dataclass
class ResultMetadata:
    tenant_id: str; environment: str; integration_id: str; connector: ConnectorIdentity; execution_id: str; task_id: str; started_at: datetime; ended_at: datetime|None; source_system: str; asset_identity: str; schema_version: str="v1"; status: Status=Status.success; error_category: ErrorCategory=ErrorCategory.none; correlation_trace_id: str|None=None
@dataclass
class ScanTask:
    task_id: str; tenant_id: str; environment: str; integration_id: str; connector_name: str; operation: str; source_system: str; asset_filter: dict[str, Any]=field(default_factory=dict); options: dict[str, Any]=field(default_factory=dict); timeout_seconds: int=30; attempt: int=1
    def validate(self):
        missing=[k for k in ("task_id","tenant_id","environment","integration_id","connector_name","operation","source_system") if not getattr(self,k)]
        if missing: raise ValueError(f"missing required task fields: {', '.join(missing)}")
        if self.timeout_seconds <= 0: raise ValueError("timeout_seconds must be positive")
@dataclass
class TaskLease: task_id: str; lease_owner: str; expires_at: datetime; version: int=1
@dataclass
class BaseRequest: metadata: ResultMetadata; options: dict[str, Any]=field(default_factory=dict)
DiscoveryRequest=BaseRequest; SchemaScanRequest=BaseRequest; FreshnessRequest=BaseRequest; ProfileRequest=BaseRequest; QualityRequest=BaseRequest; LineageRequest=BaseRequest; QueryHistoryRequest=BaseRequest
@dataclass
class ConnectionTestResult: ok: bool; message: str="ok"; error_category: ErrorCategory=ErrorCategory.none
@dataclass
class DiscoveryResult: metadata: ResultMetadata; assets: list[dict[str, Any]]=field(default_factory=list)
@dataclass
class SchemaChange: change_type: str; asset_identity: str; field_path: str; before: Any=None; after: Any=None
@dataclass
class SchemaSnapshot: metadata: ResultMetadata; canonical_schema: dict[str, Any]; fingerprint: str; changes: list[SchemaChange]=field(default_factory=list)
@dataclass
class FreshnessResult: metadata: ResultMetadata; watermarks: dict[str, Any]=field(default_factory=dict)
@dataclass
class ProfileResult: metadata: ResultMetadata; metrics: dict[str, Any]=field(default_factory=dict); raw_rows_persisted: bool=False
@dataclass
class QualityResult: metadata: ResultMetadata; checks: list[dict[str, Any]]=field(default_factory=list)
@dataclass
class LineageResult: metadata: ResultMetadata; events: list[dict[str, Any]]=field(default_factory=list)
@dataclass
class QueryHistoryResult: metadata: ResultMetadata; queries: list[dict[str, Any]]=field(default_factory=list)
@dataclass
class ConnectorCheckpoint: connector_name: str; tenant_id: str; integration_id: str; cursor: dict[str, Any]=field(default_factory=dict); updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
@dataclass
class ScannerHeartbeat: scanner_id: str; tenant_id: str; environment: str; healthy: bool; capabilities: ConnectorCapabilities; observed_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
@dataclass
class ScanError: category: ErrorCategory; message: str; retryable: bool=False
@dataclass
class ScanExecution: metadata: ResultMetadata; lease: TaskLease|None=None; result: Any=None; error: ScanError|None=None; attempts: int=1

def canonicalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    def norm(v):
        if isinstance(v, dict): return {k: norm(v[k]) for k in sorted(v)}
        if isinstance(v, list):
            return sorted((norm(x) for x in v), key=lambda x: json.dumps(x, sort_keys=True, default=str))
        if isinstance(v, str): return v.lower().strip()
        return v
    return norm(schema)
def schema_fingerprint(schema: dict[str, Any]) -> str:
    return sha256(json.dumps(canonicalize_schema(schema), sort_keys=True, separators=(",",":"), default=str).encode()).hexdigest()
def diff_schemas(before: dict[str, Any], after: dict[str, Any], asset_identity: str) -> list[SchemaChange]:
    b={c['name']:c for c in canonicalize_schema(before).get('columns',[])}; a={c['name']:c for c in canonicalize_schema(after).get('columns',[])}
    changes=[]
    for name in sorted(a.keys()-b.keys()): changes.append(SchemaChange('column_added',asset_identity,f'columns.{name}',None,a[name]))
    for name in sorted(b.keys()-a.keys()): changes.append(SchemaChange('column_removed',asset_identity,f'columns.{name}',b[name],None))
    for name in sorted(a.keys()&b.keys()):
        for f,ct in [('type','type_changed'),('nullable','nullable_changed'),('constraints','constraint_changed'),('partition','partition_changed')]:
            if b[name].get(f)!=a[name].get(f): changes.append(SchemaChange(ct,asset_identity,f'columns.{name}.{f}',b[name].get(f),a[name].get(f)))
    return changes
