"""Explicit dbt artifact schema registry (audited 2026-08-12)."""

from __future__ import annotations

import re

from .errors import DbtArtifactError, UnsupportedSchemaVersion

SUPPORTED_SCHEMA_VERSIONS = {
    "manifest": tuple(f"v{i}" for i in range(7, 13)),
    "run_results": tuple(f"v{i}" for i in range(4, 7)),
    "catalog": ("v1",),
    "freshness": tuple(f"v{i}" for i in range(2, 4)),
}

_URI = re.compile(
    r"^https://schemas\.getdbt\.com/dbt/(?P<family>manifest|run-results|catalog|sources)/v(?P<version>[0-9]+)/[^/]+\.json$"
)
_FAMILY = {"run-results": "run_results", "sources": "freshness"}


def validate_schema_uri(artifact_type: str, uri: object) -> str:
    if not isinstance(uri, str) or not uri:
        raise DbtArtifactError("invalid_artifact", "metadata.dbt_schema_version must be a valid dbt schema URI")
    match = _URI.fullmatch(uri)
    if not match:
        raise DbtArtifactError("invalid_artifact", "metadata.dbt_schema_version is malformed")
    detected_type = _FAMILY.get(match.group("family"), match.group("family"))
    if detected_type != artifact_type:
        raise DbtArtifactError("unsupported_artifact", "Artifact content does not match its declared artifact type")
    version = "v" + match.group("version")
    supported = SUPPORTED_SCHEMA_VERSIONS[artifact_type]
    if version not in supported:
        raise UnsupportedSchemaVersion(uri, supported)
    return version
