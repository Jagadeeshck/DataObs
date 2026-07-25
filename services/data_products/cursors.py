"""Opaque, scoped pagination cursors for Data Product resources."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class InvalidCursor(ValueError):
    """Raised when an opaque cursor is invalid for the requested collection."""


@dataclass(frozen=True)
class CursorContext:
    resource_type: str
    tenant_id: str
    environment: str
    filters: Mapping[str, Any]


def filter_fingerprint(filters: Mapping[str, Any]) -> str:
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class SignedCursorCodec:
    VERSION = 1

    def __init__(self, secret: bytes, *, ttl_seconds: int = 900, max_encoded_length: int = 2048) -> None:
        if len(secret) < 32:
            raise ValueError("cursor signing secret must contain at least 32 bytes")
        self._secret = secret
        self._ttl = ttl_seconds
        self._maximum = max_encoded_length

    def encode(self, context: CursorContext, sort_values: Sequence[Any], *, now: int | None = None) -> str:
        issued = int(time.time() if now is None else now)
        payload = {
            "environment": context.environment,
            "expires_at": issued + self._ttl,
            "filter_fingerprint": filter_fingerprint(context.filters),
            "issued_at": issued,
            "resource_type": context.resource_type,
            "sort_values": list(sort_values),
            "tenant_id": context.tenant_id,
            "version": self.VERSION,
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        signature = hmac.new(self._secret, body, hashlib.sha256).digest()
        encoded = base64.urlsafe_b64encode(body + b"." + signature).decode().rstrip("=")
        if len(encoded) > self._maximum:
            raise InvalidCursor("cursor exceeds maximum length")
        return encoded

    def decode(self, encoded: str, context: CursorContext, *, now: int | None = None) -> list[Any]:
        if not encoded or len(encoded) > self._maximum:
            raise InvalidCursor("invalid cursor length")
        try:
            raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            if len(raw) < 34 or raw[-33:-32] != b".":
                raise InvalidCursor("malformed cursor")
            body, signature = raw[:-33], raw[-32:]
            if not hmac.compare_digest(signature, hmac.new(self._secret, body, hashlib.sha256).digest()):
                raise InvalidCursor("invalid cursor signature")
            payload = json.loads(body)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            if isinstance(exc, InvalidCursor):
                raise
            raise InvalidCursor("malformed cursor") from exc
        expected = {
            "version": self.VERSION,
            "resource_type": context.resource_type,
            "tenant_id": context.tenant_id,
            "environment": context.environment,
            "filter_fingerprint": filter_fingerprint(context.filters),
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise InvalidCursor("cursor does not belong to this scope, route, or filter")
        timestamp = int(time.time() if now is None else now)
        if payload.get("issued_at", timestamp + 1) > timestamp or payload.get("expires_at", 0) < timestamp:
            raise InvalidCursor("cursor has expired or is not yet valid")
        values = payload.get("sort_values")
        if not isinstance(values, list) or len(values) > 4:
            raise InvalidCursor("cursor sort values are invalid")
        return values
