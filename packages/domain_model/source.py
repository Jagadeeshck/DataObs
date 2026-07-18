from typing import Any, Dict

from pydantic import Field, field_validator

from .base import ProductEntity
from .identity import deterministic_id

_SECRET_KEYS = {"password", "secret", "token", "api_key", "private_key"}


class Source(ProductEntity):
    source_type: str
    source_name: str
    endpoint: Dict[str, Any] = Field(default_factory=dict)
    location: str | None = None
    cloud_provider: str | None = None
    cloud_region: str | None = None
    credential_ref: str | None = None
    connector_type: str
    lifecycle_status: str = "active"

    @field_validator("endpoint")
    @classmethod
    def no_secrets(cls, value):
        bad = _SECRET_KEYS.intersection({str(k).lower() for k in value})
        if bad:
            raise ValueError(f"endpoint metadata must not contain secrets: {sorted(bad)}")
        return value

    @classmethod
    def build(cls, tenant_id: str, environment: str, source_name: str, source_type: str, connector_type: str, **kwargs):
        return cls(
            id=deterministic_id("source", [tenant_id, environment, source_type, source_name]),
            tenant_id=tenant_id,
            environment=environment,
            source_name=source_name,
            source_type=source_type,
            connector_type=connector_type,
            **kwargs,
        )
