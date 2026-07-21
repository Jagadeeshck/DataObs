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
_QUALITY_TPL = "dataobs-quality-results-{tenant}"
_RULES_TPL = "dataobs-rules-{tenant}"
_LINEAGE_TPL = "dataobs-lineage-{tenant}"

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
        self._es = es_client
        self._tenant = tenant_id
        self._qi = _QUALITY_TPL.format(tenant=tenant_id)
        self._ri = _RULES_TPL.format(tenant=tenant_id)
        self._li = _LINEAGE_TPL.format(tenant=tenant_id)
        self._ilm_hot_days = ilm_hot_days
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
                        "hot": {"min_age": "0ms", "actions": {}},
                        "warm": {"min_age": f"{self._ilm_hot_days}d", "actions": {"readonly": {}}},
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
            "id": doc_id,
            "tenant_id": self._tenant,
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
        offset: int = 0,
        table: Optional[str] = None,
        status: Optional[str] = None,
        dataset: Optional[str] = None,
        check_type: Optional[str] = None,
        severity: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List quality results, optionally filtered by table and/or status."""
        must: List[Dict[str, Any]] = [{"term": {"tenant_id": self._tenant}}]
        if table:
            must.append({"term": {"table": table}})
        if status:
            must.append({"term": {"status": status}})
        if dataset:
            must.append({"term": {"dataset": dataset}})
        if check_type:
            must.append({"term": {"check_type": check_type}})
        if severity:
            must.append({"term": {"severity": severity}})
        if run_id:
            must.append({"term": {"run_id": run_id}})
        try:
            resp = self._es.search(
                index=self._qi,
                query={"bool": {"must": must}},
                sort=[{"@timestamp": "desc"}],
                size=limit,
                from_=offset,
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
            "rule_id": rule_id,
            "tenant_id": self._tenant,
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

    def get_all_rules(
        self,
        limit: int = 100,
        offset: int = 0,
        dataset: Optional[str] = None,
        enabled: Optional[bool] = None,
        severity: Optional[str] = None,
        check_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return all rules for this tenant, ordered by dataset."""
        try:
            must: List[Dict[str, Any]] = [{"term": {"tenant_id": self._tenant}}]
            if dataset is not None:
                must.append({"term": {"dataset": dataset}})
            if enabled is not None:
                must.append({"term": {"enabled": enabled}})
            if severity is not None:
                must.append({"term": {"severity": severity}})
            if check_type is not None:
                must.append({"term": {"check_type": check_type}})
            resp = self._es.search(
                index=self._ri,
                query={"bool": {"must": must}},
                sort=[{"dataset": {"order": "asc", "unmapped_type": "keyword"}}],
                size=limit,
                from_=offset,
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
                query={
                    "bool": {
                        "must": [
                            {"term": {"tenant_id": self._tenant}},
                            {"term": {"dataset": dataset}},
                        ]
                    }
                },
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
            "node_id": node_id,
            "tenant_id": self._tenant,
            "doc_type": "node",
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

    def get_all_nodes(
        self, limit: int = 100, offset: int = 0, node_type: Optional[str] = None, dataset: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            must: List[Dict[str, Any]] = [
                {"term": {"tenant_id": self._tenant}},
                {"term": {"doc_type": "node"}},
            ]
            if node_type:
                must.append({"term": {"type": node_type}})
            if dataset:
                must.append({"term": {"dataset": dataset}})
            resp = self._es.search(
                index=self._li,
                query={"bool": {"must": must}},
                size=limit,
                from_=offset,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch lineage nodes")
            return []

    def save_lineage_edge(self, edge: Dict[str, Any]) -> str:
        edge_id = (
            edge.get("edge_id")
            or f"{edge.get('source_node_id', '')}->{edge.get('target_node_id', '')}"
            or str(uuid.uuid4())
        )
        doc = {
            **edge,
            "edge_id": edge_id,
            "tenant_id": self._tenant,
            "doc_type": "edge",
            "@timestamp": _now_iso(),
        }
        self._es.index(index=self._li, id=f"edge::{edge_id}", document=doc, refresh="wait_for")
        return edge_id

    def get_all_edges(
        self,
        limit: int = 100,
        offset: int = 0,
        source: Optional[str] = None,
        target: Optional[str] = None,
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            must: List[Dict[str, Any]] = [
                {"term": {"tenant_id": self._tenant}},
                {"term": {"doc_type": "edge"}},
            ]
            if source:
                must.append({"term": {"source_node_id": source}})
            if target:
                must.append({"term": {"target_node_id": target}})
            if relation:
                must.append({"term": {"relation": relation}})
            resp = self._es.search(
                index=self._li,
                query={"bool": {"must": must}},
                size=limit,
                from_=offset,
            )
            return [h["_source"] for h in resp["hits"]["hits"]]
        except Exception:
            logger.exception("Failed to fetch lineage edges")
            return []

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        visited = {node_id}
        queue = [node_id]
        affected: List[str] = []
        current_depth = 0
        while queue and current_depth < depth:
            next_queue: List[str] = []
            for current_node in queue:
                try:
                    resp = self._es.search(
                        index=self._li,
                        query={
                            "bool": {
                                "must": [
                                    {"term": {"tenant_id": self._tenant}},
                                    {"term": {"doc_type": "edge"}},
                                    {"term": {"source_node_id": current_node}},
                                ]
                            }
                        },
                        size=1000,
                    )
                    for hit in resp["hits"]["hits"]:
                        target = hit["_source"].get("target_node_id")
                        if target and target not in visited:
                            visited.add(target)
                            affected.append(target)
                            next_queue.append(target)
                except Exception:
                    logger.exception("Failed during downstream impact traversal")
            queue = next_queue
            current_depth += 1
        return affected


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
            raise ValueError("DATAOBS_STORE_BACKEND=elasticsearch requires a valid es_client.")
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
            "@timestamp": {"type": "date"},
            "id": {"type": "keyword"},
            "tenant_id": {"type": "keyword"},
            "check_name": {"type": "keyword"},
            "table": {"type": "keyword"},
            "status": {"type": "keyword"},
            "score": {"type": "float"},
            "otel_trace_id": {"type": "keyword"},
            "details": {"type": "object", "enabled": False},
        }
    }


def _rules_mapping() -> Dict[str, Any]:
    return {
        "properties": {
            "@timestamp": {"type": "date"},
            "rule_id": {"type": "keyword"},
            "tenant_id": {"type": "keyword"},
            "dataset": {"type": "keyword"},
            "check_type": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "enabled": {"type": "boolean"},
            "config": {"type": "object", "enabled": False},
        }
    }


def _lineage_mapping() -> Dict[str, Any]:
    return {
        "properties": {
            "@timestamp": {"type": "date"},
            "doc_type": {"type": "keyword"},
            "node_id": {"type": "keyword"},
            "edge_id": {"type": "keyword"},
            "source_node_id": {"type": "keyword"},
            "target_node_id": {"type": "keyword"},
            "tenant_id": {"type": "keyword"},
            "type": {"type": "keyword"},
            "upstream": {"type": "keyword"},
            "downstream": {"type": "keyword"},
            "attributes": {"type": "object", "enabled": False},
        }
    }


# Data Observability MVP Elasticsearch helpers.
from src.data_observability.mappings import DATAOBS_INDEX_TEMPLATES  # noqa: E402


def _do_index(self, short: str) -> str:
    return f"dataobs-{short}-v1-{self._tenant}"


def _install_dataobs_templates(self) -> None:
    for name, body in DATAOBS_INDEX_TEMPLATES.items():
        try:
            self._es.indices.put_index_template(name=name, **body)
        except TypeError:
            self._es.indices.put_index_template(name=name, body=body)
        except Exception:
            logger.exception("Failed to install data observability template %s", name)


def _es_upsert(self, short: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    full = {**doc, "tenant_id": self._tenant}
    self._es.index(index=_do_index(self, short), id=doc_id, document=full, refresh="wait_for")
    return full


def _es_search(self, short: str, limit: int = 100, offset: int = 0, **filters: Any) -> List[Dict[str, Any]]:
    must = [{"term": {"tenant_id": self._tenant}}]
    for k, v in filters.items():
        if v is None or k in {"q", "limit", "offset", "date_from", "date_to"}:
            continue
        if k == "asset_id" and short == "job-runs":
            must.append(
                {
                    "bool": {
                        "should": [{"term": {"input_assets": v}}, {"term": {"output_assets": v}}],
                        "minimum_should_match": 1,
                    }
                }
            )
        else:
            must.append({"term": {k: v}})
    if filters.get("q"):
        must.append({"multi_match": {"query": filters["q"], "fields": ["name", "description", "job_name", "message"]}})
    resp = self._es.search(index=_do_index(self, short), query={"bool": {"must": must}}, size=limit, from_=offset)
    return [h["_source"] for h in resp["hits"]["hits"]]


def upsert_dataobs_asset(self, asset):
    return _es_upsert(self, "assets", asset["asset_id"], asset)


def get_dataobs_asset(self, asset_id):
    try:
        return self._es.get(index=_do_index(self, "assets"), id=asset_id)["_source"]
    except NotFoundError:
        return None


def search_dataobs_assets(self, limit=100, offset=0, **filters):
    return _es_search(self, "assets", limit, offset, **filters)


def upsert_dataobs_column(self, column):
    return _es_upsert(self, "columns", f"{column.get('asset_id')}::{column.get('column_name')}", column)


def upsert_dataobs_quality_check(self, check):
    return _es_upsert(self, "quality-checks", check["check_id"], check)


def upsert_dataobs_quality_run(self, run):
    return _es_upsert(self, "quality-runs", run["run_id"], run)


def search_dataobs_quality_runs(self, limit=100, offset=0, **filters):
    return _es_search(self, "quality-runs", limit, offset, **filters)


def upsert_dataobs_job_run(self, job):
    return _es_upsert(self, "job-runs", job["job_run_id"], job)


def search_dataobs_job_runs(self, limit=100, offset=0, **filters):
    return _es_search(self, "job-runs", limit, offset, **filters)


def upsert_dataobs_lineage_edge(self, edge):
    return _es_upsert(self, "lineage-edges", edge["edge_id"], edge)


def get_dataobs_lineage(self, asset_id):
    return {
        "asset_id": asset_id,
        "upstream": _es_search(self, "lineage-edges", target_asset_id=asset_id),
        "downstream": _es_search(self, "lineage-edges", source_asset_id=asset_id),
    }


for _n, _f in {
    "_install_dataobs_templates": _install_dataobs_templates,
    "upsert_dataobs_asset": upsert_dataobs_asset,
    "get_dataobs_asset": get_dataobs_asset,
    "search_dataobs_assets": search_dataobs_assets,
    "upsert_dataobs_column": upsert_dataobs_column,
    "upsert_dataobs_quality_check": upsert_dataobs_quality_check,
    "upsert_dataobs_quality_run": upsert_dataobs_quality_run,
    "search_dataobs_quality_runs": search_dataobs_quality_runs,
    "upsert_dataobs_job_run": upsert_dataobs_job_run,
    "search_dataobs_job_runs": search_dataobs_job_runs,
    "upsert_dataobs_lineage_edge": upsert_dataobs_lineage_edge,
    "get_dataobs_lineage": get_dataobs_lineage,
}.items():
    setattr(ElasticsearchStore, _n, _f)
_old_bootstrap = ElasticsearchStore._bootstrap


def _bootstrap_with_dataobs(self):
    _old_bootstrap(self)
    self._install_dataobs_templates()


ElasticsearchStore._bootstrap = _bootstrap_with_dataobs
