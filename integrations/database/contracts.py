from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseIdentity:
    tenant: str
    environment: str
    provider: str
    integration: str
    instance: str
    database: str

    def canonical_id(self, schema: str = "", relation: str = "") -> str:
        material = "\x1f".join((*self.__dict__.values(), schema, relation)).encode()
        return f"database:{hashlib.sha256(material).hexdigest()}"


@dataclass(frozen=True)
class PartialCollectionFailure:
    code: str
    evidence_family: str
    retryable: bool
    resource_id: str
    message: str
