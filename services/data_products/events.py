from __future__ import annotations

import json
from hashlib import sha256

from packages.domain_model.data_product import DataProduct


class ProductConsistencyError(RuntimeError):
    """Raised when immutable revision evidence diverges from current state."""


def definition_checksum(product: DataProduct) -> str:
    payload = product.model_dump(mode="json", exclude={"etag", "updated_at"})
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def operation_id(tenant_id: str, environment: str, product_id: str, revision: int, idempotency_key: str) -> str:
    if not idempotency_key:
        raise ValueError("idempotency key is required")
    material = f"v1\0{tenant_id}\0{environment}\0{product_id}\0{revision}\0{idempotency_key}"
    return sha256(material.encode()).hexdigest()
