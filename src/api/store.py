"""
DataObs API — store layer.

This module provides:

1.  ``InMemoryStore``  — in-process dict-backed store (no persistence,
    default for local dev / backwards compatibility).

2.  ``RuleStore`` / ``LineageStore`` — ES-backed stores (pre-existing).

3.  ``get_store()`` — factory that returns the right implementation
    depending on ``DATAOBS_STORE_BACKEND``:

        DATAOBS_STORE_BACKEND=memory          → InMemoryStore  (default)
        DATAOBS_STORE_BACKEND=elasticsearch   → ElasticsearchStore

See ``src/api/es_store.py`` for the full Elasticsearch implementation.

Index names (ES-backed stores)
------------------------------
  dataobs-rules               — quality rule definitions
  dataobs-lineage-nodes       — lineage graph nodes
  dataobs-lineage-edges       — lineage graph edges
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch, NotFoundError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Index constants — must match LineageTracker constants in lineage.py
# ---------------------------------------------------------------------------
RULES_INDEX = "dataobs-rules"
NODE_INDEX  = "dataobs-lineage-nodes"
EDGE_INDEX  = "dataobs-lineage-edges"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# InMemoryStore — in-process fallback, no persistence across restarts
# ---------------------------------------------------------------------------

class InMemoryStore:
    """
    Simple dict-backed store.

    Exposes the same public interface as ElasticsearchStore so the API
    layer can treat both interchangeably.  State is lost on process exit.
    """

    def __init__(self) -> None:
        self._quality: Dict[str, Dict[str, Any]] = {}
        self._rules:   Dict[str, Dict[str, Any]] = {}
        self._lineage: Dict[str, Dict[str, Any]] = {}

    # ── Quality results ──────────────────────────────────────────────────

    def save_quality_result(self, result: Dict[str, Any]) -> str:
        doc_id = result.get("id") or str(uuid.uuid4())
        self._quality[doc_id] = {**result, "id": doc_id, "@timestamp": _now_iso()}
        return doc_id

    def get_quality_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        return self._quality.get(result_id)

    def list_quality_results(
        self,
        limit: int = 100,
        table: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self._quality.values())
        if table:
            results = [r for r in results if r.get("table") == table]
        if status:
            results = [r for r in results if r.get("status") == status]
        results.sort(key=lambda r: r.get("@timestamp", ""), reverse=True)
        return results[:limit]

    # ── Rules ────────────────────────────────────────────────────────────

    def add_rule(self, rule: Dict[str, Any]) -> str:
        return self.save_rule(rule)

    def save_rule(self, rule: Dict[str, Any]) -> str:
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        self._rules[rule_id] = {**rule, "rule_id": rule_id, "@timestamp": _now_iso()}
        return rule_id

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return sorted(self._rules.values(), key=lambda r: r.get("dataset", ""))

    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]:
        return [r for r in self._rules.values() if r.get("dataset") == dataset]

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    # ── Lineage ──────────────────────────────────────────────────────────

    def save_lineage_node(self, node: Dict[str, Any]) -> str:
        node_id = node.get("node_id") or str(uuid.uuid4())
        self._lineage[node_id] = {**node, "node_id": node_id, "@timestamp": _now_iso()}
        return node_id

    def get_lineage_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._lineage.get(node_id)

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        return list(self._lineage.values())

    # ── Legacy shim — get_all_edges() (no-op for in-memory) ─────────────

    def get_all_edges(self) -> List[Dict[str, Any]]:
        return []

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        return []


# ---------------------------------------------------------------------------
# RuleStore — ES-backed quality rule registry (pre-existing, kept for compat)
# ---------------------------------------------------------------------------

class RuleStore:
    """CRUD store for quality rule definitions, backed by Elasticsearch."""

    def __init__(self, es: Elasticsearch) -> None:
        self.es = es
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.es.indices.exists(index=RULES_INDEX):
            self.es.indices.create(
                index=RULES_INDEX,
                settings={"number_of_shards": 1, "number_of_replicas": 1},
                mappings={
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "rule_id":    {"type": "keyword"},
                        "dataset":    {"type": "keyword"},
                        "check_type": {"type": "keyword"},
                        "severity":   {"type": "keyword"},
                        "enabled":    {"type": "boolean"},
                        "config":     {"type": "object", "enabled": False},
                    }
                },
            )
            logger.info("Created index: %s", RULES_INDEX)

    def add_rule(self, rule: Dict[str, Any]) -> str:
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        doc = {
            "@timestamp": _now_iso(),
            "rule_id":    rule_id,
            "dataset":    rule.get("dataset", ""),
            "check_type": rule.get("check_type", rule.get("type", "")),
            "severity":   rule.get("severity", "medium"),
            "enabled":    rule.get("enabled", True),
            "config":     rule,
        }
        self.es.index(index=RULES_INDEX, id=rule_id, document=doc)
        logger.debug("Rule stored: %s", rule_id)
        return rule_id

    def get_all_rules(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(
                index=RULES_INDEX,
                query={"match_all": {}},
                size=1000,
                sort=[{"dataset": "asc"}],
            )
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch rules from Elasticsearch")
            return []

    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(
                index=RULES_INDEX,
                query={"term": {"dataset": dataset}},
                size=1000,
            )
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch rules for dataset '%s'", dataset)
            return []

    def delete_rule(self, rule_id: str) -> bool:
        try:
            self.es.delete(index=RULES_INDEX, id=rule_id)
            return True
        except NotFoundError:
            return False


# ---------------------------------------------------------------------------
# LineageStore — thin ES-backed lineage facade (pre-existing, kept for compat)
# ---------------------------------------------------------------------------

class LineageStore:
    """
    Read-only facade serving lineage queries from Elasticsearch.
    Write operations go through LineageTracker (src/quality/lineage.py).
    """

    def __init__(self, es: Elasticsearch) -> None:
        self.es = es

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(
                index=NODE_INDEX,
                query={"match_all": {}},
                size=1000,
                sort=[{"node_id": "asc"}],
            )
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch lineage nodes")
            return []

    def get_all_edges(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(
                index=EDGE_INDEX,
                query={"match_all": {}},
                size=1000,
            )
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch lineage edges")
            return []

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        """BFS downstream traversal — returns affected node IDs."""
        visited: set = set()
        queue = [node_id]
        affected: List[str] = []
        current_depth = 0

        while queue and current_depth < depth:
            next_queue: List[str] = []
            for current_node in queue:
                if current_node in visited:
                    continue
                visited.add(current_node)
                try:
                    resp = self.es.search(
                        index=EDGE_INDEX,
                        query={"term": {"source_node_id": current_node}},
                        size=100,
                        source=["target_node_id"],
                    )
                    for hit in resp["hits"]["hits"]:
                        target = hit["_source"]["target_node_id"]
                        if target not in visited:
                            next_queue.append(target)
                            if target not in affected:
                                affected.append(target)
                except Exception:
                    logger.exception("BFS edge fetch failed for node '%s'", current_node)
            queue = next_queue
            current_depth += 1

        return affected


# ---------------------------------------------------------------------------
# Convenience factory (mirrors es_store.get_store)
# ---------------------------------------------------------------------------

def get_store(
    es_client: Optional[Elasticsearch] = None,
    tenant_id: str = "default",
) -> Any:
    """
    Return the appropriate store based on ``DATAOBS_STORE_BACKEND``.

    Delegates to :func:`src.api.es_store.get_store` to avoid duplication.
    """
    from src.api.es_store import get_store as _es_get_store  # noqa: PLC0415
    return _es_get_store(es_client=es_client, tenant_id=tenant_id)
