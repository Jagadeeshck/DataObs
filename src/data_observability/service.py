from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

QUALITY_CHECK_TYPES = {"freshness", "row_count", "null_count", "duplicate_count", "schema_change", "custom_metric"}
FAIL_STATUSES = {"fail", "failed", "error", "critical"}
WARN_STATUSES = {"warn", "warning"}

def now_iso() -> str: return datetime.now(timezone.utc).isoformat()
def _id(prefix: str) -> str: return f"{prefix}_{uuid.uuid4().hex}"

def normalize_asset(doc: Dict[str, Any]) -> Dict[str, Any]:
    ts = now_iso(); asset_id = doc.get("asset_id") or doc.get("id") or _id("asset")
    out = {"asset_id": asset_id, "name": doc.get("name", asset_id), "asset_type": doc.get("asset_type", "table"), "source_system": doc.get("source_system", "unknown"), "database": doc.get("database", ""), "schema": doc.get("schema", ""), "owner": doc.get("owner", "unknown"), "domain": doc.get("domain", "unknown"), "criticality": doc.get("criticality", "medium"), "tags": doc.get("tags", []), "description": doc.get("description", ""), "created_at": doc.get("created_at", ts), "updated_at": ts, "last_seen_at": doc.get("last_seen_at", ts), "health_status": doc.get("health_status", "unknown")}
    out.update({k:v for k,v in doc.items() if k not in out}); return out

def calculate_asset_health(asset: Dict[str, Any], quality_runs: List[Dict[str, Any]], job_runs: List[Dict[str, Any]]) -> str:
    if not quality_runs and not job_runs: return "unknown"
    for run in quality_runs:
        if str(run.get("status", "")).lower() in FAIL_STATUSES and run.get("severity") == "critical": return "critical"
    for job in job_runs:
        if str(job.get("status", "")).lower() in FAIL_STATUSES: return "critical"
    if asset.get("freshness_breached") is True: return "critical"
    for run in quality_runs:
        if str(run.get("status", "")).lower() in FAIL_STATUSES | WARN_STATUSES or run.get("severity") == "warning": return "warning"
    for job in job_runs:
        if str(job.get("status", "")).lower() in {"delayed", "timeout"}: return "warning"
    if quality_runs and all(str(r.get("status", "")).lower() in {"pass", "passed", "success", "ok"} for r in quality_runs): return "healthy"
    return "unknown"

def parse_openlineage_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    job = payload.get("job") or {}; run = payload.get("run") or {}; event_type = str(payload.get("eventType", "")).upper()
    job_name = job.get("name") or payload.get("job_name") or "unknown"
    run_id = run.get("runId") or payload.get("run_id") or _id("ol_run")
    event_time = payload.get("eventTime") or payload.get("event_time") or now_iso()
    status = {"COMPLETE":"success", "FAIL":"failed", "ABORT":"failed", "START":"running"}.get(event_type, payload.get("status", "unknown"))
    def ds_id(ds: Dict[str, Any]) -> str:
        namespace = ds.get("namespace") or ds.get("source_system") or "openlineage"
        name = ds.get("name") or ds.get("asset_id") or "unknown"
        return f"{namespace}:{name}"
    inputs = payload.get("inputs") or [] ; outputs = payload.get("outputs") or []
    return {"job_name": job_name, "run_id": run_id, "event_time": event_time, "status": status,
            "input_assets": [ds_id(d) for d in inputs], "output_assets": [ds_id(d) for d in outputs], "inputs": inputs, "outputs": outputs}

class DataObservabilityService:
    def __init__(self, store: Any) -> None: self.store = store
    def create_or_update_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]: return self.store.upsert_dataobs_asset(normalize_asset(asset))
    def search_assets(self, **filters: Any) -> List[Dict[str, Any]]: return self.store.search_dataobs_assets(**filters)
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]: return self.store.get_dataobs_asset(asset_id)
    def create_or_update_column(self, column: Dict[str, Any]) -> Dict[str, Any]: return self.store.upsert_dataobs_column(column)
    def create_quality_check(self, check: Dict[str, Any]) -> Dict[str, Any]:
        if check.get("check_type") not in QUALITY_CHECK_TYPES: raise ValueError("Unsupported check_type")
        ts = now_iso(); check = {**check, "check_id": check.get("check_id") or _id("check"), "created_at": check.get("created_at", ts), "updated_at": ts}
        return self.store.upsert_dataobs_quality_check(check)
    def record_quality_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        run = {**run, "run_id": run.get("run_id") or _id("run"), "started_at": run.get("started_at", now_iso()), "finished_at": run.get("finished_at", now_iso())}
        saved = self.store.upsert_dataobs_quality_run(run); self.update_asset_health(run.get("asset_id")); return saved
    def search_quality_runs(self, **filters: Any) -> List[Dict[str, Any]]: return self.store.search_dataobs_quality_runs(**filters)
    def create_job_run(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job = {**job, "job_run_id": job.get("job_run_id") or _id("jobrun")}
        saved = self.store.upsert_dataobs_job_run(job)
        for asset_id in job.get("output_assets", []): self.update_asset_health(asset_id)
        return saved
    def search_job_runs(self, **filters: Any) -> List[Dict[str, Any]]: return self.store.search_dataobs_job_runs(**filters)
    def ingest_lineage_edge(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        edge = {**edge, "edge_id": edge.get("edge_id") or f"{edge.get('source_asset_id')}->{edge.get('target_asset_id')}:{edge.get('job_run_id','')}", "observed_at": edge.get("observed_at", now_iso())}
        return self.store.upsert_dataobs_lineage_edge(edge)
    def get_lineage(self, asset_id: str) -> Dict[str, Any]: return self.store.get_dataobs_lineage(asset_id)
    def update_asset_health(self, asset_id: Optional[str]) -> str:
        if not asset_id: return "unknown"
        asset = self.get_asset(asset_id) or {"asset_id": asset_id}
        health = calculate_asset_health(asset, self.search_quality_runs(asset_id=asset_id), self.search_job_runs(asset_id=asset_id))
        if self.get_asset(asset_id): self.create_or_update_asset({**asset, "health_status": health})
        return health
    def ingest_openlineage_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parsed = parse_openlineage_event(payload)
        for ds in parsed["inputs"] + parsed["outputs"]:
            self.create_or_update_asset({"asset_id": f"{ds.get('namespace','openlineage')}:{ds.get('name','unknown')}", "name": ds.get("name", "unknown"), "source_system": ds.get("namespace", "openlineage"), "asset_type": "table", "last_seen_at": parsed["event_time"]})
        job = self.create_job_run({"job_run_id": parsed["run_id"], "job_name": parsed["job_name"], "job_type": "openlineage", "source_system": "openlineage", "status": parsed["status"], "started_at": parsed["event_time"], "finished_at": parsed["event_time"], "duration_ms": 0, "input_assets": parsed["input_assets"], "output_assets": parsed["output_assets"], "error_message": ""})
        edges=[]
        for src in parsed["input_assets"]:
            for dst in parsed["output_assets"]: edges.append(self.ingest_lineage_edge({"source_asset_id": src, "target_asset_id": dst, "relationship_type": "produces", "job_name": parsed["job_name"], "job_run_id": parsed["run_id"], "observed_at": parsed["event_time"]}))
        return {"parsed": parsed, "job_run": job, "lineage_edges": edges}
