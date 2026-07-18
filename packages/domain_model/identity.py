from __future__ import annotations

import hashlib
import re
from typing import Iterable


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9._:-]+", "-", value.strip().lower()).strip("-")


def deterministic_id(prefix: str, parts: Iterable[str]) -> str:
    natural = "|".join(normalize_key(str(p)) for p in parts if p is not None)
    return f"{normalize_key(prefix)}-{hashlib.sha256(natural.encode()).hexdigest()[:24]}"
