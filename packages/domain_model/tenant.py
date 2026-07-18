from pydantic import Field

from .base import ProductEntity
from .identity import deterministic_id


class Tenant(ProductEntity):
    display_name: str
    namespace: str
    data_residency: str = "unspecified"
    retention_policy_ref: str | None = None

    @classmethod
    def build(cls, tenant_id: str, display_name: str, namespace: str, **kwargs):
        return cls(
            id=deterministic_id("tenant", [tenant_id]),
            tenant_id=tenant_id,
            display_name=display_name,
            namespace=namespace,
            **kwargs
        )
