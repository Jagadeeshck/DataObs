"""
Elasticsearch writer for the DataObs POC pipeline.

Writes four document types into separate POC indices:
  dataobs-poc-raw          — raw parsed records from source files
  dataobs-poc-curated      — normalised Spark-processed records
  dataobs-poc-quality      — quality check results
  dataobs-poc-lineage      — lineage events (source → dataset → curated)

All indices are created idempotently on first run.  ILM is intentionally
omitted for POC to keep the setup simple; add it for production.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from elasticsearch import Elasticsearch, helpers

logger = logging.getLogger(__name__)


class POCElasticWriter:
    def __init__(self, poc_cfg: Dict[str, Any]) -> None:
        es_cfg = poc_cfg["elasticsearch"]
        self.es = Elasticsearch(
            [es_cfg["host"]],
            basic_auth=(es_cfg.get("username", "elastic"), es_cfg.get("password", "")),
            verify_certs=es_cfg.get("verify_certs", False),
            request_timeout=60,
        )
        self.idx = es_cfg["indices"]

    def ensure_indices(self) -> None:
        """Create all required POC indices if they do not already exist."""
        _MAPPINGS = {
            self.idx["raw"]: {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "dataset":    {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                }
            },
            self.idx["curated"]: {
                "properties": {
                    "@timestamp":    {"type": "date"},
                    "dataset":       {"type": "keyword"},
                    "pipeline_name": {"type": "keyword"},
                    "dataset_name":  {"type": "keyword"},
                }
            },
            self.idx["quality"]: {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "table":      {"type": "keyword"},
                    "check_name": {"type": "keyword"},
                    "column":     {"type": "keyword"},
                    "status":     {"type": "keyword"},
                    "score":      {"type": "float"},
                }
            },
            self.idx["lineage"]: {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "source":     {"type": "keyword"},
                    "target":     {"type": "keyword"},
                    "relation":   {"type": "keyword"},
                    "dataset":    {"type": "keyword"},
                }
            },
        }
        for index_name, mapping in _MAPPINGS.items():
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name, mappings=mapping)
                logger.info("[es_writer] Created index: %s", index_name)

    def _bulk(self, index: str, docs: Iterable[Dict[str, Any]]) -> None:
        actions = ({"_index": index, "_source": doc} for doc in docs)
        success, errors = helpers.bulk(self.es, actions, stats_only=True, raise_on_error=False)
        if errors:
            logger.warning("[es_writer] %s bulk errors indexing into %s", errors, index)
        logger.info("[es_writer] Indexed %d docs into %s", success, index)

    def write_raw(self, docs: List[Dict[str, Any]]) -> None:
        self._bulk(self.idx["raw"], docs)

    def write_curated(self, docs: List[Dict[str, Any]]) -> None:
        self._bulk(self.idx["curated"], docs)

    def write_quality(self, docs: List[Dict[str, Any]]) -> None:
        self._bulk(self.idx["quality"], docs)

    def write_lineage(self, docs: List[Dict[str, Any]]) -> None:
        self._bulk(self.idx["lineage"], docs)
