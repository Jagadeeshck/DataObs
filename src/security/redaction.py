from __future__ import annotations

import re
from typing import Any

_SECRET = re.compile(
    r"(?:^|[_-])(authorization|password|secret|token|api[_-]?key|private[_-]?key|client[_-]?secret|credential|sasl|jaas|cookie|set-cookie)(?:$|[_-])",
    re.I,
)
_SAFE = {"token_expiry", "secret_reference_name"}


def redact(value: Any) -> Any:
    """Return a recursively redacted copy suitable for logs, audit and evidence."""
    if isinstance(value, dict):
        return {
            str(k): (v if str(k).lower() in _SAFE else "[REDACTED]") if _SECRET.search(str(k)) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [REDACTED]", value)
    return value
