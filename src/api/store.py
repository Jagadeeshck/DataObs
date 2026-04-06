"""In-memory stores used by the lightweight DataObs API service."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List


@dataclass
class RuleStore:
    _rules: Dict[str, dict] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def list_rules(self) -> List[dict]:
        with self._lock:
            return list(self._rules.values())

    def upsert_rule(self, rule_id: str, payload: dict) -> dict:
        with self._lock:
            record = {"rule_id": rule_id, **payload}
            self._rules[rule_id] = record
            return record

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            return self._rules.pop(rule_id, None) is not None


@dataclass
class LineageStore:
    _nodes: Dict[str, dict] = field(default_factory=dict)
    _edges: List[dict] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def upsert_node(self, node_id: str, payload: dict) -> dict:
        with self._lock:
            record = {"node_id": node_id, **payload}
            self._nodes[node_id] = record
            return record

    def list_nodes(self) -> List[dict]:
        with self._lock:
            return list(self._nodes.values())

    def add_edge(self, payload: dict) -> dict:
        with self._lock:
            self._edges.append(payload)
            return payload

    def list_edges(self) -> List[dict]:
        with self._lock:
            return list(self._edges)

    def downstream(self, root_node_id: str, depth: int = 5) -> List[str]:
        with self._lock:
            edges = list(self._edges)

        visited = set()
        queue = [root_node_id]
        affected = []
        current_depth = 0

        while queue and current_depth < depth:
            next_queue = []
            for node in queue:
                if node in visited:
                    continue
                visited.add(node)
                for edge in edges:
                    if edge.get("source_node_id") == node:
                        target = edge.get("target_node_id")
                        if target and target not in visited:
                            next_queue.append(target)
                            if target not in affected:
                                affected.append(target)
            queue = next_queue
            current_depth += 1

        return affected
