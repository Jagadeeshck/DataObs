"""Minimal redaction-safe Elasticsearch snapshot client used by Team 6 scripts."""

from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

TERMINAL_MIGRATION = "0021_lineage_analysis_explorer"


class SnapshotError(RuntimeError):
    pass


@dataclass
class ElasticsearchSnapshotClient:
    endpoint: str
    timeout: float = 30

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
        user, password = os.getenv("ELASTICSEARCH_USER"), os.getenv("ELASTICSEARCH_PASSWORD")
        if api_key:
            headers["Authorization"] = f"ApiKey {api_key}"
        elif user and password:
            encoded = base64.b64encode(f"{user}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        request = urllib.request.Request(
            f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}",
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:  # noqa: S310
                value = json.load(response)
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise SnapshotError(f"Elasticsearch request failed: {method} {path}") from exc
        if not isinstance(value, dict):
            raise SnapshotError("Elasticsearch returned a non-object response")
        return value


def verify_cluster(client: ElasticsearchSnapshotClient) -> str:
    info = client.request("GET", "/")
    version = info.get("version", {}).get("number")
    if not isinstance(version, str):
        raise SnapshotError("Elasticsearch version metadata is absent")
    migration = client.request("GET", f"/dataobs-system-migrations-v1/_doc/{TERMINAL_MIGRATION}")
    if not migration.get("found"):
        raise SnapshotError(f"terminal migration {TERMINAL_MIGRATION} is not applied")
    return version


def report(*, operation: str, repository: str, snapshot: str, version: str, status: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "operation": operation,
        "repository": repository,
        "snapshot": snapshot,
        "elasticsearch_version": version,
        "terminal_migration": TERMINAL_MIGRATION,
        "status": status,
        "redaction_status": "passed",
    }
