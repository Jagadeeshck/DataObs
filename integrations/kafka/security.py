from __future__ import annotations

import re
from typing import Any

SECRET = re.compile(r"password|secret|token|sasl\.jaas|ssl\.key", re.I)


def redact(values: dict[str, Any]) -> dict[str, Any]:
    return {key: "[REDACTED]" if SECRET.search(key) else value for key, value in values.items()}
