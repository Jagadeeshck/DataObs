"""HMAC authenticated, scope-bound search-after cursor codec."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class InvalidCursor(ValueError):
    pass


class CursorCodec:
    def __init__(self, secret: bytes, *, ttl_seconds: int = 900, maximum_length: int = 4096):
        if len(secret) < 32:
            raise ValueError("cursor secret must contain at least 32 bytes")
        self.secret, self.ttl_seconds, self.maximum_length = secret, ttl_seconds, maximum_length

    def encode(
        self,
        *,
        resource: str,
        tenant_id: str,
        environment: str,
        filters: dict[str, Any],
        sort: list[str],
        values: list[Any],
        now: int | None = None,
    ) -> str:
        issued = int(time.time() if now is None else now)
        payload = {
            "v": 1,
            "resource": resource,
            "tenant_id": tenant_id,
            "environment": environment,
            "filters": filters,
            "sort": sort,
            "values": values,
            "iat": issued,
            "exp": issued + self.ttl_seconds,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(self.secret, raw, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(raw + signature).decode().rstrip("=")
        if len(token) > self.maximum_length:
            raise InvalidCursor("cursor exceeds maximum length")
        return token

    def decode(
        self,
        token: str,
        *,
        resource: str,
        tenant_id: str,
        environment: str,
        filters: dict[str, Any],
        sort: list[str],
        now: int | None = None,
    ) -> dict[str, Any]:
        if len(token) > self.maximum_length:
            raise InvalidCursor("cursor exceeds maximum length")
        try:
            decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
            raw, supplied = decoded[:-32], decoded[-32:]
            payload = json.loads(raw)
        except Exception as exc:
            raise InvalidCursor("malformed cursor") from exc
        expected = hmac.new(self.secret, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            raise InvalidCursor("invalid cursor signature")
        current = int(time.time() if now is None else now)
        checks = [
            (payload.get("v") == 1, "version"),
            (current <= payload.get("exp", 0), "expired"),
            (payload.get("resource") == resource, "resource"),
            (payload.get("tenant_id") == tenant_id, "tenant"),
            (payload.get("environment") == environment, "environment"),
            (payload.get("filters") == filters, "filters"),
            (payload.get("sort") == sort, "sort"),
        ]
        for valid, reason in checks:
            if not valid:
                raise InvalidCursor(f"cursor {reason} mismatch")
        return payload
