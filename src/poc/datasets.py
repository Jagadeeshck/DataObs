"""
Dataset discovery and source resolution.

When ``poc.data_sources`` is empty the resolver auto-discovers suitable
public datasets from data.gov.uk via the CKAN package_search API.
Three themed default queries (transport, environment, government) are used
so the POC always has enough variety to demonstrate quality checks, lineage,
and multi-dataset dashboarding.

CKAN API docs: https://docs.ckan.org/en/2.9/api/
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CKAN_SEARCH_URL = "https://data.gov.uk/api/3/action/package_search"

# Curated default queries — one per theme.  Each resolves to the first
# resource with format csv/json/xlsx that has a downloadable URL.
DEFAULT_QUERIES: List[Dict[str, str]] = [
    {"name": "road-safety",              "query": "road safety data csv",          "theme": "transport"},
    {"name": "air-quality-monitoring",   "query": "air quality monitoring csv",     "theme": "environment"},
    {"name": "local-authority-profile",  "query": "local authority profile csv",    "theme": "government"},
]


def discover_default_datasets(max_datasets: int = 3) -> List[Dict[str, Any]]:
    """
    Auto-discover up to *max_datasets* public datasets from data.gov.uk.
    Returns a list of source dicts compatible with ``poc.data_sources``.
    """
    selected: List[Dict[str, Any]] = []
    for item in DEFAULT_QUERIES[:max_datasets]:
        logger.info("[discover] Searching data.gov.uk for: %s", item["query"])
        ds = _search_ckan(item["query"])
        if ds:
            ds["name"]  = item["name"]
            ds["theme"] = item["theme"]
            selected.append(ds)
            logger.info("[discover] Found: %s — %s", ds["name"], ds.get("title"))
        else:
            logger.warning("[discover] No result for query: %s", item["query"])
    return selected


def _search_ckan(query: str) -> Optional[Dict[str, Any]]:
    """
    Query the data.gov.uk CKAN API.  Returns a single source descriptor
    for the first result that has a downloadable CSV/JSON/XLSX resource.
    Returns None if nothing is found or the API is unreachable.
    """
    try:
        resp = requests.get(
            CKAN_SEARCH_URL,
            params={"q": query, "rows": 10, "sort": "score desc, metadata_modified desc"},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("result", {}).get("results", [])

        for dataset in results:
            for resource in dataset.get("resources", []):
                fmt = (resource.get("format") or "").lower().strip(".")
                url = (resource.get("url") or "").strip()
                if fmt in {"csv", "json", "xlsx"} and url.startswith("http"):
                    return {
                        "dataset_id":    dataset.get("name") or dataset.get("id"),
                        "title":         dataset.get("title", ""),
                        "resource_name": resource.get("name", ""),
                        "resource_url":  url,
                        "format":        fmt,
                        "source_type":   "data.gov.uk",
                        "publisher":     (dataset.get("organization") or {}).get("title", ""),
                        "tags":          [t.get("name", "") for t in dataset.get("tags", [])],
                        "license":       dataset.get("license_id", ""),
                        "last_modified": resource.get("last_modified") or resource.get("created", ""),
                    }
    except Exception as exc:  # noqa: BLE001
        logger.warning("[discover] CKAN API error for '%s': %s", query, exc)
    return None


def resolve_sources(poc_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return the list of data sources the pipeline should process.

    Priority:
    1. ``poc.data_sources`` if explicitly configured and non-empty
    2. Auto-discovery from data.gov.uk if ``source_defaults.auto_discover_if_empty: true``
    3. Empty list (pipeline will exit with a clear error message)
    """
    explicit = [s for s in (poc_cfg.get("data_sources") or []) if s]
    if explicit:
        logger.info("[sources] Using %d explicitly configured sources.", len(explicit))
        return explicit

    defaults = poc_cfg.get("source_defaults", {})
    if defaults.get("enabled", True) and defaults.get("auto_discover_if_empty", True):
        max_ds = int(defaults.get("max_datasets", 3))
        logger.info("[sources] No sources configured — auto-discovering up to %d from data.gov.uk", max_ds)
        return discover_default_datasets(max_datasets=max_ds)

    logger.error("[sources] No data sources resolved and auto-discovery is disabled.")
    return []
