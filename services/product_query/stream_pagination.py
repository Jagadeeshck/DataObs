from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


class InvalidCursor(ValueError):
    pass


@dataclass(frozen=True)
class CursorState:
    sort: list[Any]
    direction: str = "next"


class CursorCodec:
    """Integrity-protected, tenant-bound public cursor codec."""

    def __init__(self, secret: str | bytes, *, ttl_seconds: int = 900):
        key = secret.encode() if isinstance(secret, str) else secret
        if len(key) < 16:
            raise ValueError("cursor secret must contain at least 16 bytes")
        self._key = key
        self._ttl = ttl_seconds

    @staticmethod
    def fingerprint(filters: dict[str, Any]) -> str:
        canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def encode(self, state: CursorState, *, tenant: str, environment: str, filters: dict[str, Any]) -> str:
        payload = {
            "v": 1,
            "exp": int(time.time()) + self._ttl,
            "tenant": tenant,
            "environment": environment,
            "filter": self.fingerprint(filters),
            "sort": state.sort,
            "direction": state.direction,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(self._key, raw, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(raw + signature).rstrip(b"=").decode()

    def decode(self, cursor: str, *, tenant: str, environment: str, filters: dict[str, Any]) -> CursorState:
        try:
            decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
            raw, signature = decoded[:-32], decoded[-32:]
            if not hmac.compare_digest(signature, hmac.new(self._key, raw, hashlib.sha256).digest()):
                raise InvalidCursor("cursor signature is invalid")
            payload = json.loads(raw)
        except InvalidCursor:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise InvalidCursor("cursor is malformed") from exc
        if payload.get("v") != 1 or payload.get("exp", 0) < time.time():
            raise InvalidCursor("cursor is expired or unsupported")
        if payload.get("tenant") != tenant or payload.get("environment") != environment:
            raise InvalidCursor("cursor context does not match")
        if payload.get("filter") != self.fingerprint(filters):
            raise InvalidCursor("cursor filters do not match")
        if payload.get("direction") not in {"next", "previous"} or not isinstance(payload.get("sort"), list):
            raise InvalidCursor("cursor state is invalid")
        return CursorState(sort=payload["sort"], direction=payload["direction"])
