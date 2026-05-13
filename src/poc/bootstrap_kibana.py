"""
Kibana bootstrap script for the DataObs POC.

Imports the POC saved objects (index patterns + dashboards) into Kibana
using the Saved Objects import API.

Usage::

    PYTHONPATH=. python -m src.poc.bootstrap_kibana

Or via the convenience script::

    ./scripts/run_poc_pipeline.sh
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from src.poc.config import get_poc_config

logger = logging.getLogger(__name__)


def _kibana_auth(poc_cfg: dict) -> HTTPBasicAuth:
    """
    Build HTTP Basic Auth credentials for Kibana API calls.

    Resolution order (highest wins):
    1. KIBANA_USERNAME / KIBANA_PASSWORD env vars
    2. elasticsearch.username / elasticsearch.password from poc config
    3. Hardcoded defaults: elastic / changeme
    """
    es_cfg = poc_cfg.get("elasticsearch", {})
    username = (
        os.environ.get("KIBANA_USERNAME")
        or os.environ.get("ELASTIC_USERNAME")
        or es_cfg.get("username", "elastic")
    )
    password = (
        os.environ.get("KIBANA_PASSWORD")
        or os.environ.get("ELASTIC_PASSWORD")
        or es_cfg.get("password", "changeme")
    )
    return HTTPBasicAuth(username, password)


def wait_for_kibana(base_url: str, auth: HTTPBasicAuth, retries: int = 20, delay: int = 5) -> bool:
    """Poll Kibana /api/status until it reports 'green'."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(f"{base_url}/api/status", auth=auth, timeout=10)
            if resp.status_code == 200:
                status = resp.json().get("status", {}).get("overall", {}).get("level", "")
                if status in {"available", "green", "degraded"}:
                    logger.info("[kibana] Kibana is ready (status=%s).", status)
                    return True
        except Exception:  # noqa: BLE001
            pass
        logger.info("[kibana] Waiting for Kibana... attempt %d/%d", attempt, retries)
        time.sleep(delay)
    return False


def import_saved_objects(base_url: str, saved_objects_path: Path, auth: HTTPBasicAuth) -> None:
    """POST saved objects NDJSON file to Kibana import API."""
    url = f"{base_url}/api/saved_objects/_import?overwrite=true"
    headers = {"kbn-xsrf": "true"}
    with open(saved_objects_path, "rb") as fh:
        files = {"file": (saved_objects_path.name, fh, "application/ndjson")}
        resp = requests.post(url, headers=headers, files=files, auth=auth, timeout=60)
        resp.raise_for_status()
    result = resp.json()
    success = result.get("successCount", 0)
    errors  = result.get("errors", [])
    logger.info("[kibana] Imported %d saved object(s) from %s.", success, saved_objects_path)
    if errors:
        logger.warning("[kibana] %d import error(s): %s", len(errors), errors)


def create_data_views(base_url: str, patterns: list, auth: HTTPBasicAuth) -> None:
    """Create Kibana data views for all configured index patterns."""
    url = f"{base_url}/api/data_views/data_view"
    headers = {"kbn-xsrf": "true", "Content-Type": "application/json"}
    for pattern in patterns:
        payload = {
            "data_view": {
                "title": pattern,
                "timeFieldName": "@timestamp",
            }
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, auth=auth, timeout=30)
            if resp.status_code in {200, 409}:  # 409 = already exists
                logger.info("[kibana] Data view ready: %s", pattern)
            else:
                logger.warning("[kibana] Data view '%s' returned %d: %s", pattern, resp.status_code, resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[kibana] Could not create data view '%s': %s", pattern, exc)


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s \u2014 %(message)s")

    poc_cfg = get_poc_config()
    if not poc_cfg.get("enabled", False):
        logger.info("POC mode disabled. Exiting.")
        return

    dash_cfg = poc_cfg.get("dashboards", {})
    kibana_cfg = poc_cfg.get("kibana", {})
    base_url = (
        os.environ.get("KIBANA_URL")
        or dash_cfg.get("kibana_base_url")
        or kibana_cfg.get("url")
        or "http://localhost:5601"
    )
    so_file = dash_cfg.get("load_saved_objects_file", "kibana/dataobs-poc-saved-objects.ndjson")
    dv_patterns = dash_cfg.get("create_data_views", [
        "dataobs-poc-curated*",
        "dataobs-poc-quality*",
        "dataobs-poc-telemetry-*",
    ])

    auth = _kibana_auth(poc_cfg)

    if not wait_for_kibana(base_url, auth):
        logger.error("[kibana] Kibana did not become ready. Aborting dashboard bootstrap.")
        return

    if poc_cfg.get("create_kibana_data_views", True):
        create_data_views(base_url, dv_patterns, auth)

    so_path = Path(so_file)
    if poc_cfg.get("bootstrap_dashboards", True) and so_path.exists():
        import_saved_objects(base_url, so_path, auth)
    else:
        logger.info("[kibana] Skipping saved objects import (file=%s, bootstrap_dashboards=%s).",
                    so_path, poc_cfg.get("bootstrap_dashboards"))


if __name__ == "__main__":
    main()
