"""
Asset catalog search over the 0035 semantic-search projection.

Bounded, tenant- and environment-scoped keyword search across the
`dataobs-asset-search-current-v1` index (migration 0035). Ranks on a BM25
multi_match across the asset's display name, description, free-text search
field, and tags, with exact keyword filters for type/owner/classification.

This is the richer endpoint the Console catalog-browse client was written to
adopt: it preserves the same honesty contract — a measured zero (the index
answered with no matches) is distinct from unavailable (index/backend missing).
No raw payloads or secrets are returned; only catalog metadata.

Semantic (ELSER/vector) ranking is intentionally NOT enabled here yet: the 0035
mapping ships the text fields for keyword relevance now; the semantic_text layer
is a later additive step (requires an ELSER deployment). Keeping this endpoint
keyword-only keeps it runnable on a basic license and honest about its ranking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
else:
    Elasticsearch = Any

logger = logging.getLogger(__name__)

ASSET_SEARCH_INDEX = "dataobs-asset-search-current-v1"

# Exact-match keyword facets the caller may filter on.
_FACET_FIELDS = ("asset_type", "owner_team", "classification", "business_service")

_MAX_SIZE = 100


@dataclass
class AssetSearchResult:
    items: list[dict[str, Any]]
    total: int
    data_status: str  # complete | unavailable | error
    facets: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class AssetSearchRepository:
    """Tenant-scoped keyword search over the 0035 asset-search projection."""

    def __init__(self, es_client: Elasticsearch):
        self.es = es_client

    def _query(self, tenant_id: str, environment: str, text: Optional[str], filters: dict[str, str]) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if text:
            must.append(
                {
                    "multi_match": {
                        "query": text,
                        "type": "best_fields",
                        "fields": [
                            "display_name^3",
                            "search_text^2",
                            "description",
                            "tags",
                            "terms",
                        ],
                    }
                }
            )
        else:
            must.append({"match_all": {}})
        filter_clauses: list[dict[str, Any]] = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"environment": environment}},
        ]
        for facet in _FACET_FIELDS:
            value = filters.get(facet)
            if value:
                filter_clauses.append({"term": {facet: value}})
        return {"bool": {"must": must, "filter": filter_clauses}}

    def search(
        self,
        tenant_id: str,
        environment: str,
        *,
        text: Optional[str] = None,
        filters: Optional[dict[str, str]] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> AssetSearchResult:
        """Return a bounded page of catalog assets ranked by keyword relevance.

        Never raises for the caller: an unavailable index or transport error resolves
        to an explicit data_status (unavailable | error) with zero items, kept distinct
        from a measured zero (data_status=complete, total=0).
        """
        size = max(0, min(limit, _MAX_SIZE))
        from_ = max(0, offset)
        query = self._query(tenant_id, environment, text, filters or {})
        aggs = {facet: {"terms": {"field": facet, "size": 20}} for facet in _FACET_FIELDS}

        try:
            response = self.es.search(
                index=ASSET_SEARCH_INDEX,
                query=query,
                aggs=aggs,
                size=size,
                from_=from_,
                source_excludes=["search_text"],
                track_total_hits=True,
            )
        except Exception as exc:
            # Index may not exist yet (migration not applied) or ES unavailable.
            if _is_missing_index(exc):
                logger.info("asset search index %s is not present", ASSET_SEARCH_INDEX)
                return AssetSearchResult(
                    items=[],
                    total=0,
                    data_status="unavailable",
                    warnings=["asset search projection is not configured"],
                )
            logger.warning("asset search failed for tenant %s: %s", tenant_id, exc)
            return AssetSearchResult(items=[], total=0, data_status="error", warnings=[str(exc)])

        hits = response.get("hits", {})
        total_value = hits.get("total", {})
        total = total_value.get("value", 0) if isinstance(total_value, dict) else int(total_value or 0)
        items = [hit.get("_source", {}) for hit in hits.get("hits", [])]
        facets = {
            facet: [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in response.get("aggregations", {}).get(facet, {}).get("buckets", [])
            ]
            for facet in _FACET_FIELDS
        }
        return AssetSearchResult(items=items, total=total, data_status="complete", facets=facets)


def _is_missing_index(exc: Exception) -> bool:
    """True when the exception indicates the search index does not exist."""
    status = getattr(exc, "status_code", None) or getattr(exc, "meta", None) and getattr(exc.meta, "status", None)
    if status == 404:
        return True
    return "index_not_found" in str(exc) or "no such index" in str(exc).lower()
