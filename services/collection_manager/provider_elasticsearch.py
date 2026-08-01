"""Durable Elasticsearch repositories for Integration SDK provider evidence."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence

from packages.collectors.sdk import CollectionCheckpoint, IntegrationConfiguration, IntegrationContext, PaginationCursor
from packages.collectors.sdk.errors import CheckpointConflictError, InternalCollectorError

CHECKPOINT_INDEX = "dataobs-provider-checkpoints-v1"
OBSERVATION_STREAM = "logs-dataobs.provider-observation-default"
RUN_STREAM = "logs-dataobs.collection-run-default"


def _id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def _json(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _json(v) for k, v in asdict(value).items()}
    if isinstance(value, (datetime, Enum)):
        return value.isoformat() if isinstance(value, datetime) else value.value
    if isinstance(value, (set, frozenset, tuple)):
        return [_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    return value


class ElasticsearchCheckpointStore:
    def __init__(self, client: Any, *, environment: str) -> None:
        if not environment:
            raise ValueError("environment is required")
        self.client, self.environment = client, environment

    async def load(self, tenant_id: str, integration_id: str, capability: str, *, scope=None):
        doc_id = _id(tenant_id, self.environment, integration_id, capability, repr(sorted((scope or {}).items())))
        try:
            hit = self.client.get(index=CHECKPOINT_INDEX, id=doc_id)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                return None
            raise
        source = hit["_source"]
        if source["tenant_id"] != tenant_id or source["environment"] != self.environment:
            raise PermissionError("checkpoint tenant boundary violation")
        return CollectionCheckpoint(
            tenant_id,
            integration_id,
            source["provider_type"],
            capability,
            PaginationCursor(source["cursor"]) if source.get("cursor") else None,
            datetime.fromisoformat(source["watermark"]) if source.get("watermark") else None,
            source["version"],
            source.get("scope", {}),
        )

    async def save(self, checkpoint: CollectionCheckpoint, *, expected_version: int | None) -> None:
        scope = checkpoint.scope
        required = {"account", "region", "service", "capability"}
        if scope and not required <= set(scope):
            raise ValueError("scoped checkpoints require account, region, service and capability")
        doc_id = _id(
            checkpoint.tenant_id,
            self.environment,
            checkpoint.integration_id,
            checkpoint.capability,
            repr(sorted(scope.items())),
        )
        document = {
            "tenant_id": checkpoint.tenant_id,
            "environment": self.environment,
            "integration_id": checkpoint.integration_id,
            "provider_type": checkpoint.provider_type,
            "capability": checkpoint.capability,
            "scope": dict(scope),
            "cursor": checkpoint.cursor.value if checkpoint.cursor else None,
            "watermark": checkpoint.watermark.isoformat() if checkpoint.watermark else None,
            "version": checkpoint.version,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        kwargs: dict[str, Any] = {"op_type": "create"} if expected_version is None else {}
        if expected_version is not None:
            current = self.client.get(index=CHECKPOINT_INDEX, id=doc_id)
            if current["_source"]["version"] != expected_version:
                raise CheckpointConflictError("checkpoint version conflict")
            kwargs.update(if_seq_no=current["_seq_no"], if_primary_term=current["_primary_term"])
        try:
            self.client.index(index=CHECKPOINT_INDEX, id=doc_id, document=document, refresh="wait_for", **kwargs)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                raise CheckpointConflictError("checkpoint version conflict") from exc
            raise


class ElasticsearchProviderRepository:
    def __init__(self, client: Any, *, environment: str, bulk_size: int = 250) -> None:
        if not environment or not 1 <= bulk_size <= 500:
            raise ValueError("environment and bounded bulk_size are required")
        self.client, self.environment, self.bulk_size = client, environment, bulk_size

    async def persist(self, context: IntegrationContext, observations: Sequence[object]) -> None:
        for start in range(0, len(observations), self.bulk_size):
            operations = []
            for item in observations[start : start + self.bulk_size]:
                body = _json(item)
                body.update(
                    tenant_id=context.tenant_id,
                    environment=self.environment,
                    integration_id=context.integration_id,
                    collection_run_id=context.collection_run_id,
                )
                identity = body.get("canonical_id") or _id(repr(body))
                operations.extend(
                    (
                        {
                            "create": {
                                "_index": OBSERVATION_STREAM,
                                "_id": _id(context.tenant_id, self.environment, identity),
                            }
                        },
                        body,
                    )
                )
            response = self.client.bulk(operations=operations, refresh="wait_for")
            failures = [
                entry
                for entry in response.get("items", [])
                if next(iter(entry.values())).get("status", 500) not in (201, 409)
            ]
            if response.get("errors") and failures:
                raise InternalCollectorError("observation persistence partial failure")


class ElasticsearchRunRepository:
    async def persist(self, context, configuration, provider_version, result):
        # Intentionally allowlisted: provider configuration and exception messages never enter this document.
        body = {
            "@timestamp": result.completed_at.isoformat(),
            "collection_run_id": result.run_id,
            "tenant_id": context.tenant_id,
            "environment": context.attributes.get("environment", "unknown"),
            "integration_id": context.integration_id,
            "provider_type": configuration.provider_type,
            "provider_version": provider_version,
            "requested_capabilities": sorted(result.requested_capabilities),
            "completed_capabilities": sorted(result.completed_capabilities),
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
            "status": "partial" if result.partial_failures else "succeeded",
            "resource_count": result.discovered_resources,
            "observation_count": result.emitted_observations,
            "skipped_duplicate_count": result.skipped,
            "retry_count": result.retry_count,
            "partial_failure_count": len(result.partial_failures),
            "error_codes": sorted({f.error_code for f in result.partial_failures}),
            "configuration_fingerprint": _id(
                configuration.integration_id,
                configuration.provider_type,
                repr(sorted(configuration.allowed_capabilities)),
            ),
            "evidence_status": "functional_unvalidated",
        }
        self.client.index(
            index=RUN_STREAM, id=_id(context.tenant_id, body["environment"], result.run_id), document=body
        )

    def __init__(self, client: Any) -> None:
        self.client = client
