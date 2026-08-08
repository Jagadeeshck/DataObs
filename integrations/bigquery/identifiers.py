from __future__ import annotations

import re

from .errors import safe_error

PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
DATASET = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$")
LOCATION = re.compile(r"^(?:US|EU|[a-z][a-z0-9]{0,30}(?:-[a-z0-9]{1,31})*)$")


def _validate(value: object, pattern: re.Pattern[str], kind: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value) or any(ord(c) < 32 for c in value):
        raise safe_error("invalid_configuration", f"invalid {kind}")
    return value


def project_id(value: object) -> str:
    return _validate(value, PROJECT, "project identifier")


def dataset_id(value: object) -> str:
    return _validate(value, DATASET, "dataset identifier")


def location_id(value: object) -> str:
    value = _validate(value, LOCATION, "location identifier")
    return value if value in {"US", "EU"} else value.lower()
