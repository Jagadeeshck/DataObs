from __future__ import annotations

from hashlib import sha256


class ProductConsistencyError(RuntimeError):
    """Raised when immutable revision evidence diverges from current state."""


def operation_id(tenant_id: str, environment: str, product_id: str, revision: int, payload: str) -> str:
    material = f"v1\0{tenant_id}\0{environment}\0{product_id}\0{revision}\0{payload}"
    return sha256(material.encode()).hexdigest()
