"""Persistence extensions for OpenLineage projections.

The original DataObs store exposes a deliberately small compatibility surface.
This module extends both in-memory and Elasticsearch stores without forcing a
large migration of the legacy rule/quality APIs.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterable, List, Optional

from elasticsearch import ConflictError, NotFoundError

from src.api.es_store import ElasticsearchStore
from src.api.store import InMemoryStore


def _ensure_memory(store: InMemoryStore) -> None:
    defaults: Dict[str, Dict[str, Any]] = {
        "_dataobs_assets": {},
        "_dataobs_columns": {},
        "_dataobs_checks": {},
        "_dataobs_quality_runs": {},
        "_dataobs_job_runs": {},
        "_dataobs_edges": {},
        "_dataobs_jobs": {},
        "_dataobs_lineage_events": {},
        "_dataobs_column_edges": {},
    }
    for name, default in defaults.items():
        if not hasattr(store, name):
            setattr(store, name, default)


def _page(items: Iterable[Dict[str, Any]], limit: int, offset: int) -> List[Dict[str, Any]]:
    return list(items)[offset : offset + limit]


def memory_append_lineage_event(self, event):
    _ensure_memory(self)
    event_id = event["event_id"]
    if event_id in self._dataobs_lineage_events:
        return {"created": False, "event": self._dataobs_lineage_events[event_id]}
    self._dataobs_lineage_events[event_id] = dict(event)
    return {"created": True, "event": self._dataobs_lineage_events[event_id]}


def memory_get_lineage_event(self, event_id):
    _ensure_memory(self)
    return self._dataobs_lineage_events.get(event_id)


def memory_search_lineage_events(self, limit=100, offset=0, run_id=None, job_id=None, event_type=None):
    _ensure_memory(self)
    events = list(self._dataobs_lineage_events.values())
    for key, value in {"run_id": run_id, "job_id": job_id, "event_type": event_type}.items():
        if value is not None:
            events = [event for event in events if event.get(key) == value]
    events.sort(key=lambda event: event.get("@timestamp", ""), reverse=True)
    return _page(events, limit, offset)


def memory_upsert_job(self, job):
    _ensure_memory(self)
    job_id = job["job_id"]
    self._dataobs_jobs[job_id] = {**self._dataobs_jobs.get(job_id, {}), **job}
    return self._dataobs_jobs[job_id]


def memory_get_job(self, job_id):
    _ensure_memory(self)
    return self._dataobs_jobs.get(job_id)


def memory_get_job_run(self, run_id):
    _ensure_memory(self)
    direct = self._dataobs_job_runs.get(run_id)
    if direct:
        return direct
    return next((item for item in self._dataobs_job_runs.values() if item.get("source_run_id") == run_id), None)


def memory_get_lineage_edge(self, edge_id):
    _ensure_memory(self)
    return self._dataobs_edges.get(edge_id)


def memory_upsert_column_edge(self, edge):
    _ensure_memory(self)
    edge_id = edge["edge_id"]
    self._dataobs_column_edges[edge_id] = {**self._dataobs_column_edges.get(edge_id, {}), **edge}
    return self._dataobs_column_edges[edge_id]


def memory_get_column_edge(self, edge_id):
    _ensure_memory(self)
    return self._dataobs_column_edges.get(edge_id)


def memory_search_column_edges(
    self, limit=1000, offset=0, source_asset_id=None, source_column=None, target_asset_id=None, target_column=None
):
    _ensure_memory(self)
    edges = list(self._dataobs_column_edges.values())
    for key, value in {
        "source_asset_id": source_asset_id,
        "source_column": source_column,
        "target_asset_id": target_asset_id,
        "target_column": target_column,
    }.items():
        if value is not None:
            edges = [edge for edge in edges if edge.get(key) == value]
    return _page(edges, limit, offset)


def _traverse_edges(edges, asset_id, direction, depth):
    source_field, target_field = (
        ("target_asset_id", "source_asset_id") if direction == "upstream" else ("source_asset_id", "target_asset_id")
    )
    all_edges = list(edges)
    visited = {asset_id}
    nodes = []
    selected_edges = []
    queue = deque([(asset_id, 0)])
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in all_edges:
            if edge.get(source_field) != current:
                continue
            neighbour = edge.get(target_field)
            if not neighbour:
                continue
            selected_edges.append(edge)
            if neighbour in visited:
                continue
            visited.add(neighbour)
            nodes.append(neighbour)
            queue.append((neighbour, current_depth + 1))
    return {
        "asset_id": asset_id,
        "direction": direction,
        "depth": depth,
        "nodes": nodes,
        "edges": selected_edges,
        "count": len(nodes),
    }


def memory_traverse_lineage(self, asset_id, direction="downstream", depth=5):
    _ensure_memory(self)
    return _traverse_edges(self._dataobs_edges.values(), asset_id, direction, depth)


def memory_column_lineage(self, asset_id, column, direction="upstream"):
    edges = (
        memory_search_column_edges(self, target_asset_id=asset_id, target_column=column)
        if direction == "upstream"
        else memory_search_column_edges(self, source_asset_id=asset_id, source_column=column)
    )
    return {"asset_id": asset_id, "column": column, "direction": direction, "edges": edges, "count": len(edges)}


FIXED_INDICES = {
    "jobs": "dataobs-job-definitions-v1",
    "job-runs": "dataobs-job-run-current-v1",
    "lineage-events": "logs-dataobs.openlineage-default",
    "task-runs": "dataobs-task-run-current-v1",
    "stage-runs": "dataobs-stage-run-current-v1",
    "attempts": "dataobs-run-attempt-current-v1",
    "streaming-queries": "dataobs-streaming-query-current-v1",
}


def _index(store, short):
    """Resolve only server-owned fixed resources; never accept an index name from a caller."""
    return FIXED_INDICES.get(short, f"dataobs-{short}-v1")


def _document(store, short, doc_id):
    try:
        return store._es.get(index=_index(store, short), id=doc_id)["_source"]
    except NotFoundError:
        return None


def _upsert(store, short, doc_id, document):
    stored = {**document, "tenant_id": store._tenant}
    store._es.index(index=_index(store, short), id=doc_id, document=stored, refresh="wait_for")
    return stored


def _search(store, short, limit=100, offset=0, sort=None, filters=None):
    must = [{"term": {"tenant_id": store._tenant}}]
    for key, value in (filters or {}).items():
        if value is not None:
            must.append({"term": {key: value}})
    response = store._es.search(
        index=_index(store, short), query={"bool": {"must": must}}, size=limit, from_=offset, sort=sort
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]


def es_append_lineage_event(self, event):
    event_id = event["event_id"]
    stored = {**event, "tenant_id": self._tenant}
    try:
        self._es.create(index=_index(self, "lineage-events"), id=event_id, document=stored, refresh="wait_for")
        return {"created": True, "event": stored}
    except ConflictError:
        return {"created": False, "event": _document(self, "lineage-events", event_id) or stored}


def es_get_lineage_event(self, event_id):
    return _document(self, "lineage-events", event_id)


def es_search_lineage_events(self, limit=100, offset=0, run_id=None, job_id=None, event_type=None):
    return _search(
        self,
        "lineage-events",
        limit,
        offset,
        [{"@timestamp": "desc"}],
        {"run_id": run_id, "job_id": job_id, "event_type": event_type},
    )


def es_upsert_job(self, job):
    return _upsert(self, "jobs", job["job_id"], job)


def es_get_job(self, job_id):
    return _document(self, "jobs", job_id)


def es_get_job_run(self, run_id):
    return _document(self, "job-runs", run_id)


def es_get_lineage_edge(self, edge_id):
    return _document(self, "lineage-edges", edge_id)


def es_upsert_column_edge(self, edge):
    return _upsert(self, "column-lineage-edges", edge["edge_id"], edge)


def es_get_column_edge(self, edge_id):
    return _document(self, "column-lineage-edges", edge_id)


def es_search_column_edges(
    self, limit=1000, offset=0, source_asset_id=None, source_column=None, target_asset_id=None, target_column=None
):
    return _search(
        self,
        "column-lineage-edges",
        limit,
        offset,
        filters={
            "source_asset_id": source_asset_id,
            "source_column": source_column,
            "target_asset_id": target_asset_id,
            "target_column": target_column,
        },
    )


def es_traverse_lineage(self, asset_id, direction="downstream", depth=5):
    lookup_field, neighbour_field = (
        ("target_asset_id", "source_asset_id") if direction == "upstream" else ("source_asset_id", "target_asset_id")
    )
    visited = {asset_id}
    frontier = [asset_id]
    nodes = []
    selected_edges = []
    for _ in range(depth):
        if not frontier:
            break
        response = self._es.search(
            index=_index(self, "lineage-edges"),
            query={"bool": {"must": [{"term": {"tenant_id": self._tenant}}, {"terms": {lookup_field: frontier}}]}},
            size=1000,
        )
        next_frontier = []
        for hit in response["hits"]["hits"]:
            edge = hit["_source"]
            selected_edges.append(edge)
            neighbour = edge.get(neighbour_field)
            if neighbour and neighbour not in visited:
                visited.add(neighbour)
                nodes.append(neighbour)
                next_frontier.append(neighbour)
        frontier = next_frontier
    return {
        "asset_id": asset_id,
        "direction": direction,
        "depth": depth,
        "nodes": nodes,
        "edges": selected_edges,
        "count": len(nodes),
    }


def es_column_lineage(self, asset_id, column, direction="upstream"):
    edges = (
        es_search_column_edges(self, target_asset_id=asset_id, target_column=column)
        if direction == "upstream"
        else es_search_column_edges(self, source_asset_id=asset_id, source_column=column)
    )
    return {"asset_id": asset_id, "column": column, "direction": direction, "edges": edges, "count": len(edges)}


def install_store_extensions():
    memory_methods = {
        "append_dataobs_lineage_event": memory_append_lineage_event,
        "get_dataobs_lineage_event": memory_get_lineage_event,
        "search_dataobs_lineage_events": memory_search_lineage_events,
        "upsert_dataobs_job": memory_upsert_job,
        "get_dataobs_job": memory_get_job,
        "get_dataobs_job_run": memory_get_job_run,
        "get_dataobs_lineage_edge": memory_get_lineage_edge,
        "upsert_dataobs_column_lineage_edge": memory_upsert_column_edge,
        "get_dataobs_column_lineage_edge": memory_get_column_edge,
        "search_dataobs_column_lineage_edges": memory_search_column_edges,
        "traverse_dataobs_lineage": memory_traverse_lineage,
        "get_dataobs_column_lineage": memory_column_lineage,
    }
    elasticsearch_methods = {
        "append_dataobs_lineage_event": es_append_lineage_event,
        "get_dataobs_lineage_event": es_get_lineage_event,
        "search_dataobs_lineage_events": es_search_lineage_events,
        "upsert_dataobs_job": es_upsert_job,
        "get_dataobs_job": es_get_job,
        "get_dataobs_job_run": es_get_job_run,
        "get_dataobs_lineage_edge": es_get_lineage_edge,
        "upsert_dataobs_column_lineage_edge": es_upsert_column_edge,
        "get_dataobs_column_lineage_edge": es_get_column_edge,
        "search_dataobs_column_lineage_edges": es_search_column_edges,
        "traverse_dataobs_lineage": es_traverse_lineage,
        "get_dataobs_column_lineage": es_column_lineage,
    }
    for name, method in memory_methods.items():
        setattr(InMemoryStore, name, method)
    for name, method in elasticsearch_methods.items():
        setattr(ElasticsearchStore, name, method)


install_store_extensions()
