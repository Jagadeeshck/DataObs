"""
DataObs API — store layer.

Defines the unified API persistence contract plus in-memory and legacy
compatibility stores.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from elasticsearch import Elasticsearch, NotFoundError

logger = logging.getLogger(__name__)

RULES_INDEX = "dataobs-rules"
NODE_INDEX = "dataobs-lineage-nodes"
EDGE_INDEX = "dataobs-lineage-edges"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StoreProtocol(Protocol):
    def save_quality_result(self, result: Dict[str, Any]) -> str: ...
    def get_quality_result(self, result_id: str) -> Optional[Dict[str, Any]]: ...
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
    ) -> List[Dict[str, Any]]: ...
    def save_rule(self, rule: Dict[str, Any]) -> str: ...
    def add_rule(self, rule: Dict[str, Any]) -> str: ...
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]: ...
    def get_all_rules(
        self,
        limit: int = 100,
        offset: int = 0,
        dataset: Optional[str] = None,
        enabled: Optional[bool] = None,
        severity: Optional[str] = None,
        check_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...
    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]: ...
    def delete_rule(self, rule_id: str) -> bool: ...
    def save_lineage_node(self, node: Dict[str, Any]) -> str: ...
    def get_lineage_node(self, node_id: str) -> Optional[Dict[str, Any]]: ...
    def get_all_nodes(
        self, limit: int = 100, offset: int = 0, node_type: Optional[str] = None, dataset: Optional[str] = None
    ) -> List[Dict[str, Any]]: ...
    def save_lineage_edge(self, edge: Dict[str, Any]) -> str: ...
    def get_all_edges(
        self,
        limit: int = 100,
        offset: int = 0,
        source: Optional[str] = None,
        target: Optional[str] = None,
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...
    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._quality: Dict[str, Dict[str, Any]] = {}
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._lineage_nodes: Dict[str, Dict[str, Any]] = {}
        self._lineage_edges: Dict[str, Dict[str, Any]] = {}

    def save_quality_result(self, result: Dict[str, Any]) -> str:
        doc_id = result.get("id") or str(uuid.uuid4())
        self._quality[doc_id] = {**result, "id": doc_id, "@timestamp": _now_iso()}
        return doc_id

    def get_quality_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        return self._quality.get(result_id)

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
        results = list(self._quality.values())
        if table:
            results = [r for r in results if r.get("table") == table]
        if status:
            results = [r for r in results if r.get("status") == status]
        if dataset:
            results = [r for r in results if r.get("dataset") == dataset]
        results.sort(key=lambda r: r.get("@timestamp", ""), reverse=True)
        return results[offset : offset + limit]

    def add_rule(self, rule: Dict[str, Any]) -> str:
        return self.save_rule(rule)

    def save_rule(self, rule: Dict[str, Any]) -> str:
        rule_id = rule.get("rule_id") or str(uuid.uuid4())
        self._rules[rule_id] = {**rule, "rule_id": rule_id, "@timestamp": _now_iso()}
        return rule_id

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return self._rules.get(rule_id)

    def get_all_rules(
        self,
        limit: int = 100,
        offset: int = 0,
        dataset: Optional[str] = None,
        enabled: Optional[bool] = None,
        severity: Optional[str] = None,
        check_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        rules = sorted(self._rules.values(), key=lambda r: r.get("dataset", ""))
        if dataset is not None:
            rules = [r for r in rules if r.get("dataset") == dataset]
        if enabled is not None:
            rules = [r for r in rules if r.get("enabled") == enabled]
        if severity is not None:
            rules = [r for r in rules if r.get("severity") == severity]
        if check_type is not None:
            rules = [r for r in rules if r.get("check_type", r.get("type")) == check_type]
        return rules[offset : offset + limit]

    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]:
        return [r for r in self._rules.values() if r.get("dataset") == dataset]

    def delete_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def save_lineage_node(self, node: Dict[str, Any]) -> str:
        node_id = node.get("node_id") or str(uuid.uuid4())
        self._lineage_nodes[node_id] = {**node, "node_id": node_id, "@timestamp": _now_iso()}
        return node_id

    def get_lineage_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._lineage_nodes.get(node_id)

    def get_all_nodes(
        self, limit: int = 100, offset: int = 0, node_type: Optional[str] = None, dataset: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        nodes = list(self._lineage_nodes.values())
        if node_type is not None:
            nodes = [n for n in nodes if n.get("node_type", n.get("type")) == node_type]
        if dataset is not None:
            nodes = [n for n in nodes if n.get("dataset") == dataset]
        return nodes[offset : offset + limit]

    def save_lineage_edge(self, edge: Dict[str, Any]) -> str:
        edge_id = (
            edge.get("edge_id")
            or f"{edge.get('source_node_id','')}->{edge.get('target_node_id','')}"
            or str(uuid.uuid4())
        )
        self._lineage_edges[edge_id] = {**edge, "edge_id": edge_id, "@timestamp": _now_iso()}
        return edge_id

    def get_all_edges(
        self,
        limit: int = 100,
        offset: int = 0,
        source: Optional[str] = None,
        target: Optional[str] = None,
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        edges = list(self._lineage_edges.values())
        if source is not None:
            edges = [e for e in edges if e.get("source", e.get("source_node_id")) == source]
        if target is not None:
            edges = [e for e in edges if e.get("target", e.get("target_node_id")) == target]
        if relation is not None:
            edges = [e for e in edges if e.get("relation", e.get("relation_type")) == relation]
        return edges[offset : offset + limit]

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        if depth <= 0:
            return []
        adj: Dict[str, List[str]] = {}
        for edge in self._lineage_edges.values():
            src = edge.get("source_node_id")
            dst = edge.get("target_node_id")
            if src and dst:
                adj.setdefault(src, []).append(dst)
        visited = {node_id}
        impacted: List[str] = []
        q = deque([(node_id, 0)])
        while q:
            cur, d = q.popleft()
            if d >= depth:
                continue
            for nxt in adj.get(cur, []):
                if nxt in visited:
                    continue
                visited.add(nxt)
                impacted.append(nxt)
                q.append((nxt, d + 1))
        return impacted


class RuleStore:
    """Legacy ES-backed quality rule store kept as compatibility adapter."""

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
                        "rule_id": {"type": "keyword"},
                        "dataset": {"type": "keyword"},
                        "check_type": {"type": "keyword"},
                        "severity": {"type": "keyword"},
                        "enabled": {"type": "boolean"},
                        "config": {"type": "object", "enabled": False},
                    }
                },
            )

    def add_rule(self, rule: Dict[str, Any]) -> str:
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
        return rule_id

    def get_all_rules(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(index=RULES_INDEX, query={"match_all": {}}, size=1000, sort=[{"dataset": "asc"}])
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            return []

    def get_rules_for_dataset(self, dataset: str) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(index=RULES_INDEX, query={"term": {"dataset": dataset}}, size=1000)
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            return []

    def delete_rule(self, rule_id: str) -> bool:
        try:
            self.es.delete(index=RULES_INDEX, id=rule_id)
            return True
        except NotFoundError:
            return False


class LineageStore:
    """Legacy ES-backed lineage facade for old shared indices."""

    def __init__(self, es: Elasticsearch) -> None:
        self.es = es

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(index=NODE_INDEX, query={"match_all": {}}, size=1000, sort=[{"node_id": "asc"}])
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            return []

    def get_all_edges(self) -> List[Dict[str, Any]]:
        try:
            resp = self.es.search(index=EDGE_INDEX, query={"match_all": {}}, size=1000)
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception:
            return []

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        visited: set[str] = set()
        queue = [node_id]
        affected: List[str] = []
        current_depth = 0
        while queue and current_depth < depth:
            next_queue = []
            for current_node in queue:
                if current_node in visited:
                    continue
                visited.add(current_node)
                try:
                    resp = self.es.search(
                        index=EDGE_INDEX, query={"term": {"source_node_id.keyword": current_node}}, size=100
                    )
                    for hit in resp["hits"]["hits"]:
                        t = hit["_source"].get("target_node_id")
                        if t and t not in visited:
                            affected.append(t)
                            next_queue.append(t)
                except Exception:
                    pass
            queue = next_queue
            current_depth += 1
        return affected


from src.api.es_store import get_store  # noqa: E402


# Data Observability MVP methods are attached dynamically to preserve the legacy store surface.
def _matches(doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    q = filters.get("q")
    if (
        q
        and q.lower() not in str(doc.get("name", "")).lower()
        and q.lower() not in str(doc.get("description", "")).lower()
    ):
        return False
    for key, value in filters.items():
        if value is None or key in {"limit", "offset", "q", "date_from", "date_to", "asset_id"}:
            continue
        if key == "severity" and doc.get("severity") != value:
            return False
        if key == "status" and doc.get("status") != value:
            return False
        if doc.get(key) != value:
            return False
    if filters.get("asset_id") and doc.get("asset_id") != filters["asset_id"]:
        if filters.get("asset_id") not in doc.get("input_assets", []) and filters.get("asset_id") not in doc.get(
            "output_assets", []
        ):
            return False
    return True


def _ensure_dataobs(self: InMemoryStore) -> None:
    if not hasattr(self, "_dataobs_assets"):
        self._dataobs_assets = {}
        self._dataobs_columns = {}
        self._dataobs_checks = {}
        self._dataobs_quality_runs = {}
        self._dataobs_job_runs = {}
        self._dataobs_edges = {}


def upsert_dataobs_asset(self: InMemoryStore, asset: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    self._dataobs_assets[asset["asset_id"]] = {**self._dataobs_assets.get(asset["asset_id"], {}), **asset}
    return self._dataobs_assets[asset["asset_id"]]


def get_dataobs_asset(self: InMemoryStore, asset_id: str) -> Optional[Dict[str, Any]]:
    _ensure_dataobs(self)
    return self._dataobs_assets.get(asset_id)


def search_dataobs_assets(
    self: InMemoryStore, limit: int = 100, offset: int = 0, **filters: Any
) -> List[Dict[str, Any]]:
    _ensure_dataobs(self)
    items = [d for d in self._dataobs_assets.values() if _matches(d, filters)]
    return items[offset : offset + limit]


def upsert_dataobs_column(self: InMemoryStore, column: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    key = f"{column.get('asset_id')}::{column.get('column_name')}"
    self._dataobs_columns[key] = column
    return column


def upsert_dataobs_quality_check(self: InMemoryStore, check: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    self._dataobs_checks[check["check_id"]] = check
    return check


def upsert_dataobs_quality_run(self: InMemoryStore, run: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    self._dataobs_quality_runs[run["run_id"]] = run
    return run


def search_dataobs_quality_runs(
    self: InMemoryStore, limit: int = 100, offset: int = 0, **filters: Any
) -> List[Dict[str, Any]]:
    _ensure_dataobs(self)
    items = [d for d in self._dataobs_quality_runs.values() if _matches(d, filters)]
    return items[offset : offset + limit]


def upsert_dataobs_job_run(self: InMemoryStore, job: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    self._dataobs_job_runs[job["job_run_id"]] = job
    return job


def search_dataobs_job_runs(
    self: InMemoryStore, limit: int = 100, offset: int = 0, **filters: Any
) -> List[Dict[str, Any]]:
    _ensure_dataobs(self)
    items = [d for d in self._dataobs_job_runs.values() if _matches(d, filters)]
    return items[offset : offset + limit]


def upsert_dataobs_lineage_edge(self: InMemoryStore, edge: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dataobs(self)
    self._dataobs_edges[edge["edge_id"]] = edge
    return edge


def get_dataobs_lineage(self: InMemoryStore, asset_id: str) -> Dict[str, Any]:
    _ensure_dataobs(self)
    edges = list(self._dataobs_edges.values())
    return {
        "asset_id": asset_id,
        "upstream": [e for e in edges if e.get("target_asset_id") == asset_id],
        "downstream": [e for e in edges if e.get("source_asset_id") == asset_id],
    }


for _n, _f in list(locals().items()):
    if _n.startswith(("upsert_dataobs_", "get_dataobs_", "search_dataobs_")):
        setattr(InMemoryStore, _n, _f)
