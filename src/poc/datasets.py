"""
Dataset discovery and source resolution.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CKAN_SEARCH_URL = "https://data.gov.uk/api/3/action/package_search"
FIXTURE_BASE_DIR = Path("fixtures/poc")

DEFAULT_QUERIES: List[Dict[str, str]] = [
    {"name": "road-safety", "query": "road accidents personal injury great britain statistics", "theme": "transport"},
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

FALLBACK_URLS: Dict[str, Dict[str, str]] = {
    "road-safety": {
        "resource_url": "https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-casualty-last-5-years.csv",
        "format": "csv",
        "source_type": "data.gov.uk",
    },
    "air-quality-monitoring": {
        "resource_url": "https://uk-air.defra.gov.uk/openair/R_data/metadata/site_info.csv",
        "format": "csv",
        "source_type": "uk-air.defra.gov.uk",
    },
    "local-authority-profile": {
        "resource_url": "https://opendata.arcgis.com/datasets/0892f9a891614aaf82ea0fca5dc8b4d7_0.csv",
        "format": "csv",
        "source_type": "arcgis.com",
    },
}

FIXTURE_FILES: Dict[str, Dict[str, str]] = {
    "road-safety": {"filename": "road_safety_sample.csv", "format": "csv", "theme": "transport"},
    "air-quality-monitoring": {"filename": "air_quality_sample.csv", "format": "csv", "theme": "environment"},
    "local-authority-profile": {"filename": "local_authority_sample.csv", "format": "csv", "theme": "government"},
}


def discover_default_datasets(max_datasets: int = 3) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for item in DEFAULT_QUERIES[:max_datasets]:
        logger.info("[discover] Searching data.gov.uk for: %s", item["query"])
        fallback = FALLBACK_URLS.get(item["name"])
        if fallback and _url_is_reachable(fallback["resource_url"]):
            fallback_ds = dict(fallback)
            fallback_ds["name"] = item["name"]
            fallback_ds["theme"] = item["theme"]
            fallback_ds["dataset_id"] = item["name"]
            fallback_ds["title"] = item["name"].replace("-", " ").title()
            selected.append(fallback_ds)
            continue

        ds = _search_ckan(item["query"])
        if ds and _url_is_reachable(ds["resource_url"]):
            ds["name"] = item["name"]
            ds["theme"] = item["theme"]
            selected.append(ds)
            continue

        logger.warning("[discover] Skipping dataset '%s': no validated live URL", item["name"])
    return selected


def fixture_datasets(base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = (base_dir or FIXTURE_BASE_DIR).resolve()
    out: List[Dict[str, Any]] = []
    for name, meta in FIXTURE_FILES.items():
        fixture_path = (root / meta["filename"]).resolve()
        out.append(
            {
                "name": name,
                "theme": meta["theme"],
                "dataset_id": f"fixture-{name}",
                "title": f"Fixture {name}",
                "resource_name": meta["filename"],
                "resource_url": fixture_path.as_uri(),
                "format": meta["format"],
                "source_type": "fixture",
            }
        )
    return out


def _fixture_mode_enabled(poc_cfg: Dict[str, Any]) -> bool:
    env = os.environ.get("DATAOBS_POC_FIXTURE_MODE", "").lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    return bool((poc_cfg.get("source_defaults") or {}).get("fixture_mode", False))


def _looks_like_html(headers: Dict[str, Any], content_sample: bytes) -> bool:
    ctype = (headers.get("Content-Type") or "").lower()
    if "text/html" in ctype:
        return True
    sample = content_sample[:256].lstrip().lower()
    return sample.startswith(b"<!doctype html") or sample.startswith(b"<html")


def _url_is_reachable(url: str, timeout: int = 10) -> bool:
    if "webarchive.nationalarchives.gov.uk" in url:
        logger.warning("[discover] Rejecting archived URL for live demo: %s", url)
        return False
    try:
        head = requests.head(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "DataObs-POC/1.0"})
        if head.status_code < 400:
            if _looks_like_html(head.headers, b""):
                return False
            return True
    except Exception:
        pass

    try:
        get = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"Range": "bytes=0-512", "User-Agent": "DataObs-POC/1.0"},
            stream=True,
        )
        chunk = next(get.iter_content(chunk_size=512), b"")
        if get.status_code >= 400:
            return False
        if _looks_like_html(get.headers, chunk):
            logger.warning("[discover] URL looks like HTML/archive page, rejecting: %s", url)
            return False
        return True
    except Exception:
        return False


def _search_ckan(query: str) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(
            CKAN_SEARCH_URL, params={"q": query, "rows": 10, "sort": "score desc, metadata_modified desc"}, timeout=30
        )
        resp.raise_for_status()
        results = resp.json().get("result", {}).get("results", [])
        for dataset in results:
            for resource in dataset.get("resources", []):
                fmt = (resource.get("format") or "").lower().strip(".")
                url = (resource.get("url") or "").strip()
                if fmt in {"csv", "json", "xlsx"} and url.startswith("http"):
                    return {
                        "dataset_id": dataset.get("name") or dataset.get("id"),
                        "title": dataset.get("title", ""),
                        "resource_name": resource.get("name", ""),
                        "resource_url": url,
                        "format": fmt,
                        "source_type": "data.gov.uk",
                    }
    except Exception as exc:
        logger.warning("[discover] CKAN API error for '%s': %s", query, exc)
    return None


def resolve_sources(poc_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    explicit = [s for s in (poc_cfg.get("data_sources") or []) if s]
    if explicit:
        logger.info("[sources] Using %d explicitly configured sources.", len(explicit))
        return explicit

    if _fixture_mode_enabled(poc_cfg):
        logger.info("[sources] Fixture mode enabled; resolving local sample datasets.")
        return fixture_datasets()

    defaults = poc_cfg.get("source_defaults", {})
    if defaults.get("enabled", True) and defaults.get("auto_discover_if_empty", True):
        return discover_default_datasets(max_datasets=int(defaults.get("max_datasets", 3)))

    logger.error("[sources] No data sources resolved and auto-discovery is disabled.")
    return []
