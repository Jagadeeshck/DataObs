"""Bounded traversal and redaction for untrusted dbt JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .errors import DbtArtifactError


@dataclass(frozen=True)
class ArtifactLimits:
    max_bytes: int = 20_000_000
    max_resources: int = 100_000
    max_columns: int = 2_000
    max_dependencies: int = 2_000
    max_tags: int = 100
    max_description: int = 4_096
    max_depth: int = 20


FORBIDDEN_KEYS = frozenset(
    {
        "raw_sql",
        "compiled_sql",
        "raw_code",
        "compiled_code",
        "sql",
        "pre-hook",
        "post-hook",
        "env",
        "environment",
        "credentials",
        "credential",
        "token",
        "password",
        "private_key",
        "profile",
        "fixture",
        "rows",
    }
)


def validate_safe(document: Any, limits: ArtifactLimits) -> bytes:
    try:
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise DbtArtifactError("invalid_artifact", "Artifact must be finite JSON") from exc
    if len(encoded) > limits.max_bytes:
        raise DbtArtifactError(
            "artifact_too_large", "Artifact exceeds the configured byte limit", limit=limits.max_bytes
        )

    def visit(value: Any, depth: int = 0) -> None:
        if depth > limits.max_depth:
            raise DbtArtifactError("resource_limit_exceeded", "Artifact nesting exceeds the configured limit")
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("-", "_")
                if normalized in {x.replace("-", "_") for x in FORBIDDEN_KEYS} and child not in (None, "", [], {}):
                    raise DbtArtifactError(
                        "unsafe_field_detected", "Artifact contains a restricted field", field=normalized
                    )
                visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth + 1)

    visit(document)
    return encoded


def bounded_text(value: object, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "")
    return text[:limit]
