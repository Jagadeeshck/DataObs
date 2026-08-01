from __future__ import annotations

import re
from typing import Any

_SECRET = re.compile(
    r"^(authorization|password|secret|token|api_key|private_key|client_secret|credential|sasl|jaas|cookie|set-cookie)$",
    re.I,
)
_SAFE = frozenset({"token_expiry", "secret_reference_name"})


def redact(value: Any) -> Any:
    """Recursively redact secret values without destroying safe reference metadata."""
    if isinstance(value, dict):
        return {
            k: (v if k.lower() in _SAFE else "[REDACTED]" if _SECRET.match(k) else redact(v)) for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value
