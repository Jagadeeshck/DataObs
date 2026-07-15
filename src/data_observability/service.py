from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.data_observability.openlineage import (
    column_lineage_edges,
    dataset_projection,
    duration_ms,
    infer_job_type,
    parse_openlineage_event,
    quality_assertion_runs,
    schema_columns,
    stable_id,
)
from src.data_observability import store_extensions as _store_extensions  # noqa: F401

QUALITY_CHECK_TYPES = {"freshness", "row_count", "null_count", "duplicate_count", "schema_change", "custom_metric"}
FAIL_STATUSES = {"fail", "failed", "error", "critical"}
WARN_STATUSES = {"warn", "warning"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _unique(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))


def normalize_asset(doc: Dict[str, Any]) -> Dict[str, Any]:
    ts = now_iso()
    asset_id = doc.get("asset_id") or doc.get("id") or _id("asset")
    out = {
        "asset_id": asset_id,
        "name": doc.get("name", asset_id),
        "asset_type": doc.get("asset_type", "table"),
        "source_system": doc.get("source_system", "unknown"),
        "database": doc.get("database", ""),
        "schema": doc.get("schema", ""),
        "owner": doc.get("owner", "unknown"),
        "domain": doc.get("domain", "unknown"),
        "criticality": doc.get("criticality", "medium"),
        "tags": doc.get("tags", []),
        "description": doc.get("description", ""),
        "created_at": doc.get("created_at", ts),
        "updated_at": ts,
        "last_seen_at": doc.get("last_seen_at", ts),
        "health_status": doc.get("health_status", "unknown"),
    }
    out.update({key: value for key, value in doc.items() if key not in out})
    return out


def calculate_asset_health(asset: Dict[str, Any], quality_runs: List[Dict[str, Any]], job_runs: List[Dict[str, Any]]) -> str:
    if not quality_runs and not job_runs:
        return "unknown"
    for run in quality_runs:
        if str(run.get("status", "")).lower() in FAIL_STATUSES and run.get("severity") == "critical":
            return "critical"
    for job in job_runs:
        if str(job.get("status", "")).lower() in FAIL_STATUSES:
            return "critical"
    if asset.get("freshness_breached") is True:
        return "critical"
    for run in quality_runs:
        if str(run.get("status", "")).lower() in FAIL_STATUSES | WARN_STATUSES or run.get("severity") == "warning":
            return "warning"
    for job in job_runs:
        if str(job.get("status", "")).lower() in {"delayed", "timeout"}:
            return "warning"
    if quality_runs and all(str(run.get("status", "")).lower() in {"pass", "passed", "success", "ok"} for run in quality_runs):
        return "healthy"
    return "unknown"


class DataObservabilityService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def create_or_update_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.upsert_dataobs_asset(normalize_asset(asset))

    def search_assets(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.store.search_dataobs_assets(**filters)

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_dataobs_asset(asset_id)

    def create_or_update_column(self, column: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.upsert_dataobs_column(column)

    def create_quality_check(self, check: Dict[str, Any]) -> Dict[str, Any]:
        if check.get("check_type") not in QUALITY_CHECK_TYPES:
            raise ValueError("Unsupported check_type")
        ts = now_iso()
        check = {**check, "check_id": check.get("check_id") or _id("check"), "created_at": check.get("created_at", ts), "updated_at": ts}
        return self.store.upsert_dataobs_quality_check(check)

    def record_quality_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        run = {**run, "run_id": run.get("run_id") or _id("run"), "started_at": run.get("started_at", now_iso()), "finished_at": run.get("finished_at", now_iso())}
        saved = self.store.upsert_dataobs_quality_run(run)
        self.update_asset_health(run.get("asset_id"))
        return saved

    def search_quality_runs(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.store.search_dataobs_quality_runs(**filters)

    def create_job_run(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job = {**job, "job_run_id": job.get("job_run_id") or _id("jobrun")}
        saved = self.store.upsert_dataobs_job_run(job)
        for asset_id in job.get("output_assets", []):
            self.update_asset_health(asset_id)
        return saved

    def search_job_runs(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.store.search_dataobs_job_runs(**filters)

    def get_job_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_dataobs_job_run(run_id)

    def get_job(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        return self.store.get_dataobs_job(stable_id("job", namespace, name))

    def ingest_lineage_edge(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = edge.get("edge_id") or stable_id("lineage_edge", edge.get("source_asset_id"), edge.get("target_asset_id"), edge.get("job_id") or edge.get("job_name"))
        existing = self.store.get_dataobs_lineage_edge(edge_id)
        observed_at = edge.get("observed_at") or edge.get("last_seen") or now_iso()
        document = {**(existing or {}), **edge, "edge_id": edge_id, "first_seen": (existing or {}).get("first_seen", edge.get("first_seen", observed_at)), "last_seen": observed_at, "observed_at": observed_at, "active": edge.get("active", True)}
        return self.store.upsert_dataobs_lineage_edge(document)

    def ingest_column_lineage_edge(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.get_dataobs_column_lineage_edge(edge["edge_id"])
        document = {**(existing or {}), **edge, "first_seen": (existing or {}).get("first_seen", edge.get("first_seen", now_iso())), "last_seen": edge.get("last_seen", now_iso()), "active": edge.get("active", True)}
        return self.store.upsert_dataobs_column_lineage_edge(document)

    def get_lineage(self, asset_id: str) -> Dict[str, Any]:
        return self.store.get_dataobs_lineage(asset_id)

    def traverse_lineage(self, asset_id: str, direction: str, depth: int) -> Dict[str, Any]:
        if direction not in {"upstream", "downstream"}:
            raise ValueError("direction must be upstream or downstream")
        return self.store.traverse_dataobs_lineage(asset_id, direction=direction, depth=depth)

    def get_column_lineage(self, asset_id: str, column: str, direction: str = "upstream") -> Dict[str, Any]:
        if direction not in {"upstream", "downstream"}:
            raise ValueError("direction must be upstream or downstream")
        return self.store.get_dataobs_column_lineage(asset_id, column, direction=direction)

    def update_asset_health(self, asset_id: Optional[str]) -> str:
        if not asset_id:
            return "unknown"
        asset = self.get_asset(asset_id) or {"asset_id": asset_id}
        health = calculate_asset_health(asset, self.search_quality_runs(asset_id=asset_id), self.search_job_runs(asset_id=asset_id))
        if self.get_asset(asset_id):
            self.create_or_update_asset({**asset, "health_status": health})
        return health

    def _upsert_openlineage_asset(self, projection: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_asset(projection["asset_id"]) or {}
        useful = {key: value for key, value in projection.items() if value is not None and value != "" and value != []}
        return self.create_or_update_asset({**existing, **useful})

    def _project_job(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.get_dataobs_job(parsed["job_id"]) or {}
        document = {
            **existing,
            "job_id": parsed["job_id"],
            "qualified_name": parsed["job_qualified_name"],
            "namespace": parsed["job_namespace"],
            "name": parsed["job_name"],
            "job_type": infer_job_type(parsed["job_namespace"]),
            "producer": parsed["producer"],
            "facets": {**(existing.get("facets") or {}), **parsed["job_facets"]},
            "first_seen": existing.get("first_seen", parsed["event_time"]),
            "last_seen": parsed["event_time"],
        }
        return self.store.upsert_dataobs_job(document)

    def _project_job_run(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_job_run(parsed["run_id"]) or {}
        started_at = parsed["event_time"] if parsed["event_type"] == "START" else existing.get("started_at") or parsed["event_time"]
        finished_at = parsed["event_time"] if parsed["terminal"] else existing.get("finished_at")
        error_facet = parsed["run_facets"].get("errorMessage") or {}
        nominal_facet = parsed["run_facets"].get("nominalTime") or {}
        inputs = _unique(list(existing.get("input_assets", [])) + parsed["input_assets"])
        outputs = _unique(list(existing.get("output_assets", [])) + parsed["output_assets"])
        document = {
            **existing,
            "job_run_id": parsed["run_id"],
            "job_id": parsed["job_id"],
            "job_namespace": parsed["job_namespace"],
            "job_name": parsed["job_name"],
            "job_type": infer_job_type(parsed["job_namespace"]),
            "source_system": parsed["job_namespace"],
            "status": parsed["status"],
            "last_event_type": parsed["event_type"],
            "last_event_time": parsed["event_time"],
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms(started_at, finished_at),
            "input_assets": inputs,
            "output_assets": outputs,
            "error_message": error_facet.get("message") or existing.get("error_message", ""),
            "nominal_start_time": nominal_facet.get("nominalStartTime"),
            "nominal_end_time": nominal_facet.get("nominalEndTime"),
            "producer": parsed["producer"],
            "facets": {**(existing.get("facets") or {}), **parsed["run_facets"]},
            "event_count": int(existing.get("event_count", 0)) + 1,
        }
        return self.create_job_run(document)

    def ingest_openlineage_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parsed = parse_openlineage_event(payload)
        raw_event = {
            "@timestamp": parsed["event_time"], "ingested_at": now_iso(), "event_id": parsed["event_id"],
            "event_type": parsed["event_type"], "producer": parsed["producer"], "schema_url": parsed["schema_url"],
            "run_id": parsed["run_id"], "job_id": parsed["job_id"], "job_namespace": parsed["job_namespace"],
            "job_name": parsed["job_name"], "input_assets": parsed["input_assets"], "output_assets": parsed["output_assets"],
            "facets": {"run": parsed["run_facets"], "job": parsed["job_facets"], "inputs": [dataset.get("facets", {}) for dataset in parsed["inputs"]], "outputs": [dataset.get("facets", {}) for dataset in parsed["outputs"]]},
            "raw_event": payload,
        }
        persisted = self.store.append_dataobs_lineage_event(raw_event)
        if not persisted["created"]:
            return {"event_id": parsed["event_id"], "event_type": parsed["event_type"], "deduplicated": True, "job_run": self.get_job_run(parsed["run_id"]), "lineage_edges": [], "column_lineage_edges": [], "quality_runs": []}

        job = self._project_job(parsed)
        assets, columns = [], []
        for dataset in parsed["inputs"] + parsed["outputs"]:
            assets.append(self._upsert_openlineage_asset(dataset_projection(dataset, parsed["event_time"])))
            for column in schema_columns(dataset, parsed["event_time"]):
                columns.append(self.create_or_update_column(column))
        job_run = self._project_job_run(parsed)
        lineage_edges = []
        for source in parsed["input_assets"]:
            for target in parsed["output_assets"]:
                lineage_edges.append(self.ingest_lineage_edge({"edge_id": stable_id("lineage_edge", source, target, parsed["job_id"]), "source_asset_id": source, "target_asset_id": target, "relationship_type": "produces", "edge_type": "DATASET_TO_DATASET", "job_id": parsed["job_id"], "job_name": parsed["job_name"], "job_run_id": parsed["run_id"], "observed_at": parsed["event_time"]}))
        projected_column_edges = [self.ingest_column_lineage_edge(edge) for edge in column_lineage_edges(parsed["outputs"], job_id=parsed["job_id"], run_id=parsed["run_id"], observed_at=parsed["event_time"])]
        projected_quality_runs = [self.record_quality_run(run) for run in quality_assertion_runs(parsed["inputs"] + parsed["outputs"], run_id=parsed["run_id"], observed_at=parsed["event_time"])]
        return {"event_id": parsed["event_id"], "event_type": parsed["event_type"], "deduplicated": False, "parsed": parsed, "job": job, "job_run": job_run, "assets": assets, "columns": columns, "lineage_edges": lineage_edges, "column_lineage_edges": projected_column_edges, "quality_runs": projected_quality_runs}
