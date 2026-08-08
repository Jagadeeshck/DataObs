from __future__ import annotations

import re

_SECRET_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}",
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
        r"\b(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*[^\s,;]{6,}",
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+",
        r"\bAKIA[0-9A-Z]{16}\b",
    )
)


def validate_safe_text(value: str, *, field: str, maximum: int, allow_empty: bool = False) -> str:
    """Reject unsafe operator prose without reflecting its contents in errors."""
    if not allow_empty and not value.strip():
        raise ValueError(f"{field} is required")
    if len(value) > maximum:
        raise ValueError(f"{field} exceeds server limit")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
        raise ValueError(f"{field} contains control characters")
    if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
        raise ValueError(f"{field} appears to contain a credential")
    return value
