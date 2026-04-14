"""
Elasticsearch-backed persistence for the DataObs API.

Drop-in replacement for src/api/store.py. Toggle via:
    DATAOBS_STORE_BACKEND=elasticsearch

Resolves: https://github.com/Jagadeeshck/DataObs/issues/26
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

QUALITY_INDEX = "dataobs-quality-results"
RULES_INDEX = "dataobs-rules"
LINEAGE_INDEX = "dataobs-lineage"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ElasticsearchStore:
    """
    API store backed by Elasticsearch.

    Args:
        es_client: Pre-configured elasticsearch.Elasticsearch client.
        tenant_id: Tenant identifier appended to index names.
    """

    def __init__(self, es_client: Any, tenant_id: str = "default") -> None:
        self._es = es_client
        self._tenant = tenant_id
        self._qi = f"{QUALITY_INDEX}-{tenant_id}"
        self._ri = f"{RULES_INDEX}-{tenant_id}"
        self._li = f"{LINEAGE_INDEX}-{tenant_id}"
        self._bootstrap_indices()

    # ── Quality Results ──────────────────────────────────────────────────────

    def save_quality_result(self, result: dict[str, Any]) -> str:
        doc_id = result.get("id") or str(uuid.uuid4())
        self._es.index(
            index=self._qi,
            id=doc_id,
            body={**result, "id": doc_id, "created_at": _now_iso(), "tenant_id": self._tenant},
            refresh="wait_for",
        )
        return doc_id

    def get_quality_result(self, result_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = self._es.get(index=self._qi, id=result_id)
            return resp["_source"]
        except Exception:
            return None

    def list_quality_results(self, limit: int = 100) -> list[dict[str, Any]]:
        resp = self._es.search(
            index=self._qi,
            body={"query": {"match_all": {}}, "sort": [{"created_at": "desc"}], "size": limit},
        )
        return [h["_source"] for h in resp["hits"]["hits"]]

    # ── Rules ────────────────────────────────────────────────────────────────

    def save_rule(self, rule: dict[str, Any]) -> str:
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        self._es.index(
            index=self._ri,
            id=rule_id,
            body={**rule, "rule_id": rule_id, "created_at": _now_iso(), "tenant_id": self._tenant},
            refresh="wait_for",
        )
        return rule_id

    def get_rule(self, rule_id: str) -> Optional[dict[str, Any]]:
        try:
            return self._es.get(index=self._ri, id=rule_id)["_source"]
        except Exception:
            return None

    def list_rules(self) -> list[dict[str, Any]]:
        resp = self._es.search(index=self._ri, body={"query": {"match_all": {}}, "size": 1000})
        return [h["_source"] for h in resp["hits"]["hits"]]

    # ── Lineage ──────────────────────────────────────────────────────────────

    def save_lineage_node(self, node: dict[str, Any]) -> str:
        node_id = node.get("node_id") or str(uuid.uuid4())
        self._es.index(
            index=self._li,
            id=node_id,
            body={**node, "node_id": node_id, "created_at": _now_iso(), "tenant_id": self._tenant},
            refresh="wait_for",
        )
        return node_id

    def get_lineage_node(self, node_id: str) -> Optional[dict[str, Any]]:
        try:
            return self._es.get(index=self._li, id=node_id)["_source"]
        except Exception:
            return None

    # ── Bootstrap ────────────────────────────────────────────────────────────

    def _bootstrap_indices(self) -> None:
        ilm_policy = {
            "phases": {
                "hot": {"min_age": "0ms", "actions": {"rollover": {"max_age": "7d"}}},
                "warm": {"min_age": "7d", "actions": {"readonly": {}}},
                "delete": {"min_age": "90d", "actions": {"delete": {}}},
            }
        }
        for idx in (self._qi, self._ri, self._li):
            if not self._es.indices.exists(index=idx):
                self._es.indices.create(index=idx, body={"settings": {}})


def get_store(es_client: Any = None, tenant_id: str = "default") -> Any:
    """
    Factory: returns ElasticsearchStore or falls back to in-memory store.

    Controlled by DATAOBS_STORE_BACKEND env var.
    """
    backend = os.getenv("DATAOBS_STORE_BACKEND", "memory")
    if backend == "elasticsearch" and es_client is not None:
        return ElasticsearchStore(es_client, tenant_id=tenant_id)

    # Lazy import to keep backward compat
    from src.api.store import InMemoryStore  # type: ignore[import]
    return InMemoryStore()
