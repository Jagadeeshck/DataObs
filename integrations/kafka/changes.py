from __future__ import annotations

from typing import Any

from .security import redact


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    old, new = redact(before), redact(after)
    return {
        key: {"before": old.get(key), "after": new.get(key)}
        for key in sorted(set(old) | set(new))
        if old.get(key) != new.get(key)
    }
