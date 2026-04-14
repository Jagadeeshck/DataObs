"""
DataObs API — Elasticsearch-backed stores for Rules and Lineage.

Both stores use Elasticsearch as the single source of truth so that:
  - state survives container restarts
  - multiple API replicas share the same data
  - data is queryable from Kibana / Grafana without a separate DB

Index names
-----------
  dataobs-rules               — quality rule definitions
  dataobs-lineage-nodes       — lineage graph nodes  (mirrors LineageTracker)
  dataobs-lineage-edges       — lineage graph edges  (mirrors LineageTracker)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch, NotFoundError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Index constants — must match LineageTracker constants in lineage.py
# ---------------------------------------------------------------------------
RULES_INDEX = "dataobs-rules"
NODE_INDEX = "dataobs-lineage-nodes"
EDGE_INDEX = "dataobs-lineage-edges"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# RuleStore — ES-backed quality rule registry
# ---------------------------------------------------------------------------

class RuleStore:
    """CRUD store for quality rule definitions, backed by Elasticsearch."""

    def __init__(self, es: Elasticsearch) -> None:
        self.es = es
        self._ensure_index()

    # ── index bootstrap ───────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        if not self.es.indices.exists(index=RULES_INDEX):
            self.es.indices.create(
                index=RULES_INDEX,
                settings={"number_of_shards": 1, "number_of_replicas": 1},
                mappings={
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "rule_id": {"type": "keyword"},
                        "dataset": {"type": "keyword"},
                        "check_type": {"type": "keyword"},
                        "severity": {"type": "keyword"},
                        "enabled": {"type": "boolean"},
                        "config": {"type": "object", "enabled": False},
                    }
                },
            )
            logger.info("Created index: %s", RULES_INDEX)

    # ── public API ────────────────────────────────────────────────────────

    def add_rule(self, rule: Dict[str, Any]) -> str:
        """Persist a new rule. Returns the generated rule_id."""
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        doc = {
            "@timestamp": _now_iso(),
            "rule_id": rule_id,
            "dataset": rule.get("dataset", ""),
            "check_type": rule.get("check_type", rule.get("type", "")),
            "severity": rule.get("severity", "medium"),
            "enabled": rule.get("enabled", True),
            "config": rule,
        }
        self.es.index(index=RULES_INDEX, id=rule_id, document=doc)
        logger.debug("Rule stored: %s", rule_id)
        return rule_id

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Return all rules ordered by dataset."""
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
        """Return all rules for a specific dataset."""
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
        """Delete a rule by ID. Returns True if deleted, False if not found."""
        try:
            self.es.delete(index=RULES_INDEX, id=rule_id)
            return True
        except NotFoundError:
            return False


# ---------------------------------------------------------------------------
# LineageStore — thin facade over the ES-backed lineage graph
# ---------------------------------------------------------------------------

class LineageStore:
    """
    Read-only facade that serves lineage queries from Elasticsearch.
    Write operations go through LineageTracker (in src/quality/lineage.py)
    to keep the BFS + upsert logic in one place.
    """

    def __init__(self, es: Elasticsearch) -> None:
        self.es = es

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Return all lineage nodes."""
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
        """Return all lineage edges."""
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
        """
        BFS downstream traversal — returns affected node IDs.
        Mirrors LineageTracker.get_downstream_impact() for API use.
        """
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
                    hits = resp["hits"]["hits"]
                    if len(hits) == 100:
                        logger.warning(
                            "BFS truncated at 100 edges for node '%s' depth %d",
                            current_node, current_depth,
                        )
                    for hit in hits:
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
