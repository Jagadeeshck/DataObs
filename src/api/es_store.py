"""
DataObs API — Elasticsearch-backed persistence layer.

Drop-in replacement for the in-memory store.  Toggle via:
    DATAOBS_STORE_BACKEND=elasticsearch  (default: memory)

Features
--------
- Quality results, rules, and lineage stored in per-tenant ES indices
- ILM policy: hot (7 d) → warm (30 d) → delete (90 d) — configurable
- Read-your-writes consistency via refresh="wait_for" on critical writes
- Multi-tenant index isolation enforced at the store layer
- Connection pooling via the elasticsearch-py sync client

Resolves: https://github.com/Jagadeeshck/DataObs/issues/26
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
# Index name templates  (tenant_id is substituted at init time)
# ---------------------------------------------------------------------------
_QUALITY_TPL  = "dataobs-quality-results-{tenant}"
_RULES_TPL    = "dataobs-rules-{tenant}"
_LINEAGE_TPL  = "dataobs-lineage-{tenant}"

_ILM_POLICY_NAME = "dataobs-api-ilm"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ElasticsearchStore — primary durable store
# ---------------------------------------------------------------------------

class ElasticsearchStore:
    """
    Durable API store backed by Elasticsearch.

    All three document types (quality results, rules, lineage nodes) are kept
    in separate per-tenant indices.  Index names follow the pattern::

        dataobs-quality-results-<tenant_id>
        dataobs-rules-<tenant_id>
        dataobs-lineage-<tenant_id>

    Args:
        es_client: Configured ``elasticsearch.Elasticsearch`` instance.
        tenant_id: Tenant identifier appended to every index name.
                   Use ``"default"`` for single-tenant deployments.
        ilm_hot_days:    Days before moving to warm phase (default 7).
        ilm_delete_days: Days before deletion (default 90).
    """

    def __init__(
        self,
        es_client: Elasticsearch,
        tenant_id: str = "default",
        ilm_hot_days: int = 7,
        ilm_delete_days: int = 90,
    ) -> None:
        self._es            = es_client
        self._tenant        = tenant_id
        self._qi            = _QUALITY_TPL.format(tenant=tenant_id)
        self._ri            = _RULES_TPL.format(tenant=tenant_id)
        self._li            = _LINEAGE_TPL.format(tenant=tenant_id)
        self._ilm_hot_days  = ilm_hot_days
        self._ilm_delete_days = ilm_delete_days
        self._bootstrap()

    # ── Bootstrap: ILM + indices ─────────────────────────────────────────

    def _bootstrap(self) -> None:
        """Idempotently create the ILM policy and all three indices."""
        self._ensure_ilm_policy()
        for idx, mapping in [
            (self._qi, _quality_mapping()),
            (self._ri, _rules_mapping()),
            (self._li, _lineage_mapping()),
        ]:
            self._ensure_index(idx, mapping)

    def _ensure_ilm_policy(self) -> None:
        try:
            self._es.ilm.get_lifecycle(name=_ILM_POLICY_NAME)
        except Exception:
            self._es.ilm.put_lifecycle(
                name=_ILM_POLICY_NAME,
                policy={
                    "phases": {
                        "hot":  {"min_age": "0ms",  "actions": {}},
                        "warm": {"min_age": f"{self._ilm_hot_days}d",   "actions": {"readonly": {}}},
                        "delete": {"min_age": f"{self._ilm_delete_days}d", "actions": {"delete": {}}},
                    }
                },
            )
            logger.info("Created ILM policy: %s", _ILM_POLICY_NAME)

    def _ensure_index(self, index: str, mapping: Dict[str, Any]) -> None:
        if not self._es.indices.exists(index=index):
            self._es.indices.create(
                index=index,
                settings={
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index.lifecycle.name": _ILM_POLICY_NAME,
                },
                mappings=mapping,
            )
            logger.info("Created index: %s", index)

    # ── Quality results ──────────────────────────────────────────────────

    def save_quality_result(self, result: Dict[str, Any]) -> str:
        """
        Persist a quality check result.  Returns the document ID.

        Mandatory fields in *result*:
            check_name (str), table (str), status (str), score (float)

        Optional:
            otel_trace_id (str) — trace correlation
        """
        doc_id = result.get("id") or str(uuid.uuid4())
        doc = {
            **result,
            "id":         doc_id,
            "tenant_id":  self._tenant,
            "@timestamp": result.get("@timestamp", _now_iso()),
        }
        self._es.index(
            index=self._qi,
            id=doc_id,
            document=doc,
            refresh="wait_for",
        )
        logger.debug("Quality result saved: %s", doc_id)
        return doc_id

    def get_quality_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single quality result by ID."""
        try:
            return self._es.get(index=self._qi, id=result_id)["_source"]
        except NotFoundError:
            return None
        except Exception:
            logger.exception("Failed to fetch quality result '%s'", result_id)
            return None

    def list_quality_results(
        self,
        limit: int = 100,
        table: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List quality results, optionally filtered by table and/or status."""
        must: List[Dict[str, Any]] = [{"term": {"tenant_id": self._tenant}}]
        if table:
            must.append({"term": {"table": table}})
        if status:
            must.append({"term": {"status": status}})
        try:
            resp = self._es.search(
                index=self._qi,
                query={"bool": {"must": must}},
                sort=[{"@timestamp": "desc"}],
                size=limit,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to list quality results")
            return []

    # ── Rules ────────────────────────────────────────────────────────────

    def save_rule(self, rule: Dict[str, Any]) -> str:
        """Persist or replace a quality rule.  Returns the rule_id."""
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        doc = {
            **rule,
            "rule_id":    rule_id,
            "tenant_id":  self._tenant,
            "@timestamp": _now_iso(),
        }
        self._es.index(
            index=self._ri,
            id=rule_id,
            document=doc,
            refresh="wait_for",
        )
        logger.debug("Rule saved: %s", rule_id)
        return rule_id

    # Alias kept for backward compat with RuleStore.add_rule() call sites
    def add_rule(self, rule: Dict[str, Any]) -> str:
        return self.save_rule(rule)

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._es.get(index=self._ri, id=rule_id)["_source"]
        except NotFoundError:
            return None
        except Exception:
            logger.exception("Failed to fetch rule '%s'", rule_id)
            return None

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Return all rules for this tenant, ordered by dataset."""
        try:
            resp = self._es.search(
                index=self._ri,
                query={"term": {"tenant_id": self._tenant}},
                sort=[{"dataset": {"order": "asc", "unmapped_type": "keyword"}}],
                size=1000,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch rules")
            return []

    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]:
        """Return rules for a specific dataset."""
        try:
            resp = self._es.search(
                index=self._ri,
                query={"bool": {"must": [
                    {"term": {"tenant_id": self._tenant}},
                    {"term": {"dataset": dataset}},
                ]}},
                size=1000,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch rules for dataset '%s'", dataset)
            return []

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule. Returns True if deleted, False if not found."""
        try:
            self._es.delete(index=self._ri, id=rule_id, refresh="wait_for")
            return True
        except NotFoundError:
            return False

    # ── Lineage ──────────────────────────────────────────────────────────

    def save_lineage_node(self, node: Dict[str, Any]) -> str:
        """Persist a lineage node. Returns the node_id."""
        node_id = node.get("node_id") or str(uuid.uuid4())
        doc = {
            **node,
            "node_id":    node_id,
            "tenant_id":  self._tenant,
            "@timestamp": _now_iso(),
        }
        self._es.index(
            index=self._li,
            id=node_id,
            document=doc,
            refresh="wait_for",
        )
        return node_id

    def get_lineage_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._es.get(index=self._li, id=node_id)["_source"]
        except NotFoundError:
            return None
        except Exception:
            logger.exception("Failed to fetch lineage node '%s'", node_id)
            return None

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        try:
            resp = self._es.search(
                index=self._li,
                query={"term": {"tenant_id": self._tenant}},
                size=1000,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch lineage nodes")
            return []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_store(
    es_client: Optional[Elasticsearch] = None,
    tenant_id: str = "default",
) -> Any:
    """
    Return the appropriate store implementation.

    Controlled by the ``DATAOBS_STORE_BACKEND`` environment variable:

    * ``elasticsearch`` — durable ES-backed store (requires *es_client*)
    * ``memory`` (default) — in-process dict store, state lost on restart
    """
    backend = os.getenv("DATAOBS_STORE_BACKEND", "memory").lower()
    if backend == "elasticsearch":
        if es_client is None:
            raise ValueError(
                "DATAOBS_STORE_BACKEND=elasticsearch requires a valid es_client."
            )
        logger.info("Using ElasticsearchStore (tenant=%s)", tenant_id)
        return ElasticsearchStore(es_client, tenant_id=tenant_id)

    logger.info("Using InMemoryStore (state will not survive restarts)")
    from src.api.store import InMemoryStore  # type: ignore[import]
    return InMemoryStore()


# ---------------------------------------------------------------------------
# Elasticsearch index mappings
# ---------------------------------------------------------------------------

def _quality_mapping() -> Dict[str, Any]:
    return {
        "properties": {
            "@timestamp":     {"type": "date"},
            "id":             {"type": "keyword"},
            "tenant_id":      {"type": "keyword"},
            "check_name":     {"type": "keyword"},
            "table":          {"type": "keyword"},
            "status":         {"type": "keyword"},
            "score":          {"type": "float"},
            "otel_trace_id":  {"type": "keyword"},
            "details":        {"type": "object", "enabled": False},
        }
    }


def _rules_mapping() -> Dict[str, Any]:
    return {
        "properties": {
            "@timestamp":  {"type": "date"},
            "rule_id":     {"type": "keyword"},
            "tenant_id":   {"type": "keyword"},
            "dataset":     {"type": "keyword"},
            "check_type":  {"type": "keyword"},
            "severity":    {"type": "keyword"},
            "enabled":     {"type": "boolean"},
            "config":      {"type": "object", "enabled": False},
        }
    }


def _lineage_mapping() -> Dict[str, Any]:
    return {
        "properties": {
            "@timestamp":  {"type": "date"},
            "node_id":     {"type": "keyword"},
            "tenant_id":   {"type": "keyword"},
            "type":        {"type": "keyword"},
            "upstream":    {"type": "keyword"},
            "downstream":  {"type": "keyword"},
            "attributes":  {"type": "object", "enabled": False},
        }
    }
