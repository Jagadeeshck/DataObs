from __future__ import annotations

import re
from typing import Any, Mapping

_SECRET_KEYS = re.compile(r"(?i)(authorization|password|passwd|secret|token|api[_-]?key|credential|external[_-]?id)")
_INLINE = re.compile(r"(?i)(bearer\s+|password=|token=|secret=|api[_-]?key=)([^\s,;&]+)")


def redact_text(value: object, *, limit: int = 512) -> str:
    return _INLINE.sub(lambda match: f"{match.group(1)}[REDACTED]", str(value))[:limit]


def redact_mapping(value: Mapping[str, Any], *, depth: int = 0) -> dict[str, Any]:
    if depth >= 8:
        return {"truncated": True}
    safe: dict[str, Any] = {}
    for key, item in list(value.items())[:100]:
        if _SECRET_KEYS.search(str(key)):
            safe[str(key)] = "[REDACTED]"
        elif isinstance(item, Mapping):
            safe[str(key)] = redact_mapping(item, depth=depth + 1)
        elif isinstance(item, str):
            safe[str(key)] = redact_text(item)
        elif isinstance(item, (str, int, float, bool)) or item is None:
            safe[str(key)] = item
        else:
            safe[str(key)] = redact_text(item)
    return safe
