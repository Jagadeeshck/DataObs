"""Elasticsearch-backed Command Center projector.

Reads the authoritative per-pillar read-models for a tenant/environment, runs the pure
`aggregate_summary`, and writes the result to `dataobs-command-center-summary-v1-write`
(the migration-managed alias the Console reads back through `-read`).

Each source read is independently guarded: if an index is missing or a query fails, that
source is marked not-available so the summary is honestly `complete=False` and the
affected pillar stays `unknown` — never silently healthy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .aggregator import aggregate_summary

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
else:
    Elasticsearch = Any

logger = logging.getLogger(__name__)

WRITE_INDEX = "dataobs-command-center-summary-v1-write"

# source key -> read index it aggregates from
_SOURCES = {
    "incidents": "dataobs-incidents-v1-read",
    "quality": "dataobs-quality-current-v1-read",
    "freshness": "dataobs-freshness-current-v1-read",
    "lineage": "dataobs-lineage-current-v1-read",
    "streams": "dataobs-stream-clusters-v1-read",
}


class CommandCenterProjector:
    """Aggregate per-pillar read-models into the Command Center summary projection."""

    def __init__(self, es_client: Elasticsearch):
        self.es = es_client

    def _read(self, index: str, tenant_id: str, environment: str, size: int = 1000) -> tuple[list[dict], bool]:
        """Return (docs, available). available=False when the index/query could not answer."""
        query = {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"environment": environment}},
                ]
            }
        }
        try:
            response = self.es.search(index=index, query=query, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]], True
        except Exception as exc:  # missing index / transport error
            logger.info("command-center source %s unavailable: %s", index, exc)
            return [], False

    def project(self, tenant_id: str, environment: str) -> dict[str, Any]:
        """Read all sources, aggregate, write the summary, and return it."""
        reads: dict[str, list[dict]] = {}
        available: dict[str, bool] = {}
        for key, index in _SOURCES.items():
            docs, ok = self._read(index, tenant_id, environment)
            reads[key] = docs
            available[key] = ok

        summary = aggregate_summary(
            tenant_id,
            environment,
            incidents=reads["incidents"],
            quality=reads["quality"],
            freshness=reads["freshness"],
            lineage=reads["lineage"],
            streams=reads["streams"],
            sources_available=available,
        )
        self.es.index(
            index=WRITE_INDEX,
            id=f"{tenant_id}:{environment}",
            document=summary,
            refresh=True,
        )
        logger.info(
            "projected command-center summary for %s/%s: overall=%s complete=%s",
            tenant_id,
            environment,
            summary["overall_health"],
            summary["data_status"]["complete"],
        )
        return summary
