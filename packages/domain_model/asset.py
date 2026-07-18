from datetime import datetime
from typing import List

from .base import ProductEntity
from .identity import deterministic_id

ASSET_TYPES = {
    "database",
    "schema",
    "table",
    "view",
    "materialized_view",
    "column",
    "file",
    "object",
    "topic",
    "queue",
    "stream",
    "job",
    "pipeline",
    "dashboard",
    "model",
    "application",
    "service",
}


class Asset(ProductEntity):
    fully_qualified_name: str
    namespace: str
    asset_type: str
    owner: str | None = None
    classification: str | None = None
    tags: List[str] = []
    schema_fingerprint: str | None = None
    freshness_state: str | None = None
    quality_state: str | None = None
    lifecycle_state: str = "active"
    last_observed: datetime | None = None

    @classmethod
    def build(
        cls,
        tenant_id: str,
        environment: str,
        namespace: str,
        fully_qualified_name: str,
        asset_type: str,
        source_id: str,
        **kwargs
    ):
        return cls(
            id=deterministic_id(
                "asset", [tenant_id, environment, source_id, namespace, fully_qualified_name, asset_type]
            ),
            tenant_id=tenant_id,
            environment=environment,
            namespace=namespace,
            fully_qualified_name=fully_qualified_name,
            asset_type=asset_type,
            source_id=source_id,
            **kwargs
        )
