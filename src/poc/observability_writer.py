"""
Data-observability document emitter for the POC pipeline.

Translates the patterns from Soda, Monte Carlo and Acceldata into a small
set of Elasticsearch indices the user can browse in Kibana Discover:

  dataobs-assets       — data asset catalog entries
  dataobs-quality      — quality / contract check results
  dataobs-freshness    — freshness lag / SLA breaches
  dataobs-volume       — row-count / volume anomaly observations
  dataobs-schema       — schema snapshots and drift events
  dataobs-lineage      — source → target lineage events
  dataobs-alerts       — incident-style alerts derived from checks

The emitter is intentionally synchronous and tolerant: every method
catches and logs ES errors so a failed write never breaks the pipeline.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from elasticsearch import Elasticsearch, helpers

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_schema(columns: List[Dict[str, str]]) -> str:
    payload = "|".join(f"{c['name']}:{c['type']}" for c in sorted(columns, key=lambda c: c["name"]))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


class ObservabilityWriter:
    """Writes data-observability documents into the unified ES cluster."""

    def __init__(self, host: str, password: str, tenant: str = "poc",
                 username: str = "elastic") -> None:
        self.es = Elasticsearch(
            [host],
            basic_auth=(username, password),
            verify_certs=False,
            request_timeout=30,
        )
        self.tenant = tenant

    # ── single-doc helpers ──────────────────────────────────────────────
    def _index(self, index: str, doc: Dict[str, Any]) -> None:
        try:
            self.es.index(index=index, document=doc)
        except Exception as exc:
            logger.warning("[obs_writer] failed to index into %s: %s", index, exc)

    def _bulk(self, index: str, docs: Iterable[Dict[str, Any]]) -> int:
        actions = ({"_index": index, "_source": d} for d in docs)
        try:
            success, errors = helpers.bulk(self.es, actions, stats_only=True, raise_on_error=False)
            if errors:
                logger.warning("[obs_writer] %d bulk errors indexing into %s", errors, index)
            return success
        except Exception as exc:
            logger.warning("[obs_writer] bulk failure into %s: %s", index, exc)
            return 0

    # ── high-level emitters ─────────────────────────────────────────────
    def register_asset(
        self,
        *,
        asset_id: str,
        name: str,
        asset_type: str,
        platform: str,
        location: str,
        owner: str = "dataobs-poc",
        tags: Optional[List[str]] = None,
        row_count: int = 0,
        column_count: int = 0,
        size_bytes: int = 0,
        reliability_score: float = 100.0,
    ) -> None:
        doc = {
            "@timestamp": _now(),
            "asset.id": asset_id,
            "asset.name": name,
            "asset.type": asset_type,
            "asset.platform": platform,
            "asset.location": location,
            "asset.owner": owner,
            "asset.tags": tags or [],
            "asset.row_count": row_count,
            "asset.column_count": column_count,
            "asset.size_bytes": size_bytes,
            "asset.last_updated": _now(),
            "asset.reliability_score": reliability_score,
            "tenant": self.tenant,
        }
        self._index("dataobs-assets", doc)

    def emit_quality_check(
        self,
        *,
        run_id: str,
        asset_id: str,
        asset_name: str,
        check_name: str,
        check_type: str,
        column: Optional[str],
        value: float,
        threshold: float,
        status: str,
        severity: str = "warning",
        expression: str = "",
        score: Optional[float] = None,
        message: str = "",
    ) -> None:
        doc = {
            "@timestamp": _now(),
            "run_id": run_id,
            "tenant": self.tenant,
            "asset.id": asset_id,
            "asset.name": asset_name,
            "check.name": check_name,
            "check.type": check_type,
            "check.column": column,
            "check.expression": expression,
            "check.threshold": threshold,
            "check.value": value,
            "check.status": status,
            "check.severity": severity,
            "check.message": message,
            "score": score if score is not None else (100.0 if status == "pass" else 0.0),
        }
        self._index("dataobs-quality", doc)
        if status != "pass":
            self.emit_alert(
                title=f"{check_type} check failed on {asset_name}",
                source="quality",
                rule=check_name,
                severity=severity,
                asset_id=asset_id,
                asset_name=asset_name,
                details={"value": value, "threshold": threshold, "message": message},
            )

    def emit_freshness(
        self,
        *,
        asset_id: str,
        asset_name: str,
        last_seen: str,
        lag_seconds: int,
        sla_seconds: int,
    ) -> None:
        status = "ok" if lag_seconds <= sla_seconds else "stale"
        doc = {
            "@timestamp": _now(),
            "asset.id": asset_id,
            "asset.name": asset_name,
            "freshness.last_seen": last_seen,
            "freshness.lag_seconds": lag_seconds,
            "freshness.sla_seconds": sla_seconds,
            "freshness.status": status,
            "tenant": self.tenant,
        }
        self._index("dataobs-freshness", doc)
        if status == "stale":
            self.emit_alert(
                title=f"Freshness SLA breach on {asset_name}",
                source="freshness",
                rule="freshness_sla",
                severity="warning",
                asset_id=asset_id,
                asset_name=asset_name,
                details={"lag_seconds": lag_seconds, "sla_seconds": sla_seconds},
            )

    def emit_volume(
        self,
        *,
        asset_id: str,
        asset_name: str,
        row_count: int,
        expected_min: int,
        expected_max: int,
    ) -> None:
        if row_count < expected_min or row_count > expected_max:
            status = "anomaly"
        else:
            status = "ok"
        delta_pct = 0.0
        if expected_max > 0:
            delta_pct = round((row_count - expected_max) / expected_max * 100.0, 2)
        doc = {
            "@timestamp": _now(),
            "asset.id": asset_id,
            "asset.name": asset_name,
            "volume.row_count": row_count,
            "volume.expected_min": expected_min,
            "volume.expected_max": expected_max,
            "volume.delta_pct": delta_pct,
            "volume.status": status,
            "tenant": self.tenant,
        }
        self._index("dataobs-volume", doc)
        if status == "anomaly":
            self.emit_alert(
                title=f"Volume anomaly on {asset_name}",
                source="volume",
                rule="row_count_band",
                severity="warning",
                asset_id=asset_id,
                asset_name=asset_name,
                details={
                    "row_count": row_count,
                    "expected_min": expected_min,
                    "expected_max": expected_max,
                },
            )

    def snapshot_schema(
        self,
        *,
        asset_id: str,
        asset_name: str,
        columns: List[Dict[str, str]],
        previous_hash: Optional[str] = None,
    ) -> str:
        h = _hash_schema(columns)
        drift = "stable"
        added: List[str] = []
        removed: List[str] = []
        if previous_hash and previous_hash != h:
            drift = "drift_detected"
        doc = {
            "@timestamp": _now(),
            "asset.id": asset_id,
            "asset.name": asset_name,
            "schema.snapshot_hash": h,
            "schema.columns": columns,
            "schema.drift_event": drift,
            "schema.added_columns": added,
            "schema.removed_columns": removed,
            "tenant": self.tenant,
        }
        self._index("dataobs-schema", doc)
        if drift == "drift_detected":
            self.emit_alert(
                title=f"Schema drift on {asset_name}",
                source="schema",
                rule="schema_drift",
                severity="critical",
                asset_id=asset_id,
                asset_name=asset_name,
                details={"new_hash": h, "previous_hash": previous_hash},
            )
        return h

    def emit_lineage(
        self,
        *,
        run_id: str,
        source: str,
        target: str,
        relation: str = "transformation",
        pipeline: str = "dataobs-pipeline",
        row_count: int = 0,
        fields: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        doc = {
            "@timestamp": _now(),
            "run_id": run_id,
            "tenant": self.tenant,
            "source": source,
            "target": target,
            "source_index": source,
            "sink_index": target,
            "relation": relation,
            "lineage_type": relation,
            "pipeline": pipeline,
            "row_count": row_count,
            "fields": fields or [],
        }
        self._index("dataobs-lineage", doc)

    def emit_alert(
        self,
        *,
        title: str,
        source: str,
        rule: str,
        severity: str,
        asset_id: str,
        asset_name: str,
        details: Dict[str, Any],
    ) -> None:
        doc = {
            "@timestamp": _now(),
            "alert.id": f"{source}-{rule}-{int(time.time() * 1000)}",
            "alert.title": title,
            "alert.severity": severity,
            "alert.status": "open",
            "alert.source": source,
            "alert.rule": rule,
            "asset.id": asset_id,
            "asset.name": asset_name,
            "tenant": self.tenant,
            "details": details,
        }
        self._index("dataobs-alerts", doc)
