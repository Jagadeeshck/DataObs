"""Opaque, versioned Elasticsearch search-after cursors."""

from __future__ import annotations

import base64
import json
from typing import Any


def encode_cursor(sort_values: list[Any]) -> str:
    payload = json.dumps({"v": 1, "sort": sort_values}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(value: str | None) -> list[Any] | None:
    if not value:
        return None
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid asset catalog cursor") from exc
    if decoded.get("v") != 1 or not isinstance(decoded.get("sort"), list):
        raise ValueError("Unsupported asset catalog cursor")
    return decoded["sort"]
