from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

Direction = Literal["upstream", "downstream", "both"]


def stable_id(prefix: str, *parts: object) -> str:
    canonical = json.dumps(parts, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return f"{prefix}_{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"


@dataclass(frozen=True)
class SchemaColumn:
    name: str
    data_type: str
    nullable: bool | None = None
    constraints: tuple[str, ...] = ()
    ordinal: int | None = None


@dataclass(frozen=True)
class SchemaVersion:
    asset_id: str
    observed_at: str
    provider: str
    columns: tuple[SchemaColumn, ...]
    partition_fields: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: float = 1.0
    data_status: str = "available"

    @property
    def fingerprint(self) -> str:
        body = {"columns": [asdict(c) for c in self.columns], "partition_fields": self.partition_fields}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @property
    def version_id(self) -> str:
        return stable_id("schema", self.asset_id, self.provider, self.fingerprint)


@dataclass(frozen=True)
class LineageEdge:
    edge_id: str
    source_asset_id: str
    target_asset_id: str
    level: Literal["dataset", "column"] = "dataset"
    source_column: str | None = None
    target_column: str | None = None
    relationship_type: Literal["direct", "correlated", "inferred", "unknown"] = "unknown"
    job_id: str | None = None
    run_id: str | None = None
    observed_at: str = ""
    first_seen: str = ""
    active: bool = True
    stale: bool = False
    confidence: float = 0.5
    evidence_refs: tuple[str, ...] = ()
    source_provider: str = "unknown"
    schema_version: str = "v1"

    @classmethod
    def create(cls, source_asset_id: str, target_asset_id: str, **values: object) -> "LineageEdge":
        level = str(values.get("level", "dataset"))
        edge_id = stable_id(
            "edge",
            level,
            source_asset_id,
            values.get("source_column"),
            target_asset_id,
            values.get("target_column"),
            values.get("job_id"),
        )
        return cls(edge_id=edge_id, source_asset_id=source_asset_id, target_asset_id=target_asset_id, **values)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ImpactRequest:
    root_asset_id: str
    root_column: str | None = None
    schema_change_id: str | None = None
    direction: Direction = "downstream"
    max_depth: int = 5
    max_nodes: int = 200
    max_edges: int = 500
    max_paths: int = 20
    include_stale_edges: bool = False
    as_of: str | None = None
    include_contextual_overlays: bool = True

    def validate(self) -> None:
        if not (1 <= self.max_depth <= 10 and 1 <= self.max_nodes <= 1000 and 1 <= self.max_edges <= 2500):
            raise ValueError("analysis bounds exceed the supported range")
        if not 1 <= self.max_paths <= 50:
            raise ValueError("max_paths exceeds the supported range")

    def analysis_id(self, tenant_id: str, environment: str) -> str:
        return stable_id("impact", tenant_id, environment, asdict(self))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
