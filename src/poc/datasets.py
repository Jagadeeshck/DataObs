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

# Curated default queries \u2014 one per theme.  Each resolves to the first
# resource with format csv/json/xlsx that has a downloadable URL.
# NOTE: queries are intentionally narrow so CKAN returns a stable,
# well-known dataset rather than a stale/404 resource.
DEFAULT_QUERIES: List[Dict[str, str]] = [
    {
        "name": "road-safety",
        "query": "road accidents personal injury great britain statistics",
        "theme": "transport",
    },
    {
        "name": "air-quality-monitoring",
        "query": "automatic urban rural network air quality data csv",
        "theme": "environment",
    },
    {
        "name": "local-authority-profile",
        "query": "local authority district names codes england wales csv",
        "theme": "government",
    },
]

# Stable fallback URLs used when CKAN auto-discovery returns an
# unreachable resource.  These are long-lived ONS / data.gov.uk endpoints.
FALLBACK_URLS: Dict[str, Dict[str, str]] = {
    "road-safety": {
        "resource_url": (
            "https://data.dft.gov.uk/road-accidents-safety-data/"
            "dft-road-casualty-statistics-casualty-last-5-years.csv"
        ),
        "format": "csv",
        "source_type": "data.gov.uk",
    },
    "air-quality-monitoring": {
        "resource_url": (
            "https://uk-air.defra.gov.uk/datastore/data_files/"
            "site_information.csv"
        ),
        "format": "csv",
        "source_type": "uk-air.defra.gov.uk",
    },
    "local-authority-profile": {
        "resource_url": (
            "https://opendata.arcgis.com/datasets/"
            "0892f9a891614aaf82ea0fca5dc8b4d7_0.csv"
        ),
        "format": "csv",
        "source_type": "arcgis.com",
    },
}


def discover_default_datasets(max_datasets: int = 3) -> List[Dict[str, Any]]:
    """
    Auto-discover up to *max_datasets* public datasets from data.gov.uk.
    Falls back to FALLBACK_URLS when CKAN returns a resource that is
    unreachable (404 / DNS failure detected at resolve time).
    Returns a list of source dicts compatible with ``poc.data_sources``.
    """
    selected: List[Dict[str, Any]] = []
    for item in DEFAULT_QUERIES[:max_datasets]:
        logger.info("[discover] Searching data.gov.uk for: %s", item["query"])
        ds = _search_ckan(item["query"])
        if ds:
            # Validate the resolved URL is reachable before committing
            if _url_is_reachable(ds["resource_url"]):
                ds["name"] = item["name"]
                ds["theme"] = item["theme"]
                selected.append(ds)
                logger.info("[discover] Found: %s \u2014 %s", ds["name"], ds.get("title"))
                continue
            else:
                logger.warning(
                    "[discover] CKAN URL unreachable for %s (%s) \u2014 using fallback.",
                    item["name"],
                    ds["resource_url"],
                )

        # Use hardcoded fallback
        fallback = FALLBACK_URLS.get(item["name"])
        if fallback:
            fallback_ds = dict(fallback)
            fallback_ds["name"] = item["name"]
            fallback_ds["theme"] = item["theme"]
            fallback_ds["dataset_id"] = item["name"]
            fallback_ds["title"] = item["name"].replace("-", " ").title()
            selected.append(fallback_ds)
            logger.info("[discover] Using fallback for %s: %s", item["name"], fallback_ds["resource_url"])
        else:
            logger.warning("[discover] No result and no fallback for query: %s", item["query"])

    return selected


def _url_is_reachable(url: str, timeout: int = 10) -> bool:
    """HEAD-check a URL; return True only on a 2xx/3xx HTTP status."""
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        return resp.status_code < 400
    except Exception:  # noqa: BLE001
        return False


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
        logger.info("[sources] No sources configured \u2014 auto-discovering up to %d from data.gov.uk", max_ds)
        return discover_default_datasets(max_datasets=max_ds)

    logger.error("[sources] No data sources resolved and auto-discovery is disabled.")
    return []
