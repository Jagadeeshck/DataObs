"""
ML anomaly-detector registry — binds quality monitors to native Elasticsearch ML jobs.

This is the persistence + lifecycle layer for the `detection_mode: auto` feature.
When a monitor opts into automatic (rule-free) anomaly detection, the registry:

  1. derives an MLJobConfig from the monitor,
  2. creates/starts the native ES ML anomaly-detection job via ElasticsearchMLManager,
  3. writes a strict metadata-only record into `dataobs-ml-anomaly-detectors-v1`
     (migration 0034) tracking provisioning and availability state.

On monitor deactivation/deletion it stops+deletes the ML job and marks the record
deactivated. State is honest: a record is only `active` once the ES job is actually
open; failures are recorded as `error` with a reason code, never silently dropped and
never reported as healthy.

Metadata only: no raw sample values, no SQL, no secrets are persisted here.

Requires an Elasticsearch Enterprise (X-Pack ML) license at runtime. When ML is
unavailable the registry records `provisioning_state=error` rather than failing the
monitor create/delete call — monitor lifecycle must not hard-depend on ML availability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from src.analytics.elasticsearch_ml import ElasticsearchMLManager, MLJobConfig

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch
else:
    Elasticsearch = Any

logger = logging.getLogger(__name__)

ML_DETECTOR_INDEX = "dataobs-ml-anomaly-detectors-v1"

# Monitor types whose canonical observation metric maps to an ES ML detector.
# Each entry: (detector_function, detector_field, index_pattern_template).
_DETECTOR_MAP = {
    "freshness": ("high_mean", "age_seconds", "dataobs-freshness*"),
    "volume": ("mean", "row_count", "dataobs-quality-results*"),
    "metric": ("mean", "metric_value", "dataobs-quality-results*"),
    "throughput": ("mean", "metric_value", "dataobs-quality-results*"),
    "error_rate": ("high_mean", "metric_value", "dataobs-quality-results*"),
}

# Monitor types that cannot be served by a numeric ML detector.
UNSUPPORTED_REASON = "monitor_type_not_ml_detectable"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detector_config_for_monitor(monitor: Any) -> Optional[MLJobConfig]:
    """Derive an MLJobConfig from a monitor, or None if the type is not ML-detectable.

    Pure and deterministic — no I/O. The job id is tenant/environment/monitor scoped so
    it is stable across restarts and unique per tenant.
    """
    monitor_type = getattr(monitor.monitor_type, "value", str(monitor.monitor_type))
    mapping = _DETECTOR_MAP.get(monitor_type)
    if mapping is None:
        return None
    function, field, index_pattern = mapping
    job_id = f"dataobs-{monitor.tenant_id}-{monitor.environment}-{monitor.id}".lower()
    return MLJobConfig(
        job_id=job_id,
        description=f"DataObs auto anomaly detection for monitor {monitor.id} ({monitor_type})",
        index_pattern=index_pattern,
        detector_function=function,
        detector_field=field,
    )


@dataclass
class DetectorRecord:
    tenant_id: str
    environment: str
    monitor_id: str
    ml_job_id: str
    datafeed_id: str
    detection_mode: str
    detector_function: str
    detector_field: str
    index_pattern: str
    provisioning_state: str  # provisioning | active | error | deactivated
    availability_state: str  # available | unavailable | unknown
    configured: bool
    created_at: str
    updated_at: str
    last_error_code: Optional[str] = None

    def to_doc(self) -> dict[str, Any]:
        doc = {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "monitor_id": self.monitor_id,
            "ml_job_id": self.ml_job_id,
            "datafeed_id": self.datafeed_id,
            "detection_mode": self.detection_mode,
            "detector_function": self.detector_function,
            "detector_field": self.detector_field,
            "index_pattern": self.index_pattern,
            "provisioning_state": self.provisioning_state,
            "availability_state": self.availability_state,
            "configured": self.configured,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.last_error_code is not None:
            doc["last_error_code"] = self.last_error_code
        return doc


class MLDetectorRegistry:
    """Tenant-scoped registry binding monitors to native ES ML anomaly jobs."""

    def __init__(self, es_client: Elasticsearch, ml_manager: ElasticsearchMLManager | None = None):
        self.es = es_client
        self.ml = ml_manager or ElasticsearchMLManager(es_client)

    def _doc_id(self, tenant_id: str, environment: str, monitor_id: str) -> str:
        return f"{tenant_id}:{environment}:{monitor_id}"

    def register(self, monitor: Any) -> DetectorRecord:
        """Provision and persist an ML detector for a monitor opting into auto detection.

        Writes the metadata record first in `provisioning` state, attempts to create and
        start the ES ML job, then updates the record to `active` or `error`. The monitor
        create flow should call this but must not fail if provisioning errors — the record
        carries the honest error state for the Console and runtime to surface.
        """
        config = detector_config_for_monitor(monitor)
        doc_id = self._doc_id(monitor.tenant_id, monitor.environment, monitor.id)

        if config is None:
            record = DetectorRecord(
                tenant_id=monitor.tenant_id,
                environment=monitor.environment,
                monitor_id=monitor.id,
                ml_job_id="",
                datafeed_id="",
                detection_mode="auto",
                detector_function="",
                detector_field="",
                index_pattern="",
                provisioning_state="error",
                availability_state="unavailable",
                configured=False,
                created_at=_now(),
                updated_at=_now(),
                last_error_code=UNSUPPORTED_REASON,
            )
            self.es.index(index=ML_DETECTOR_INDEX, id=doc_id, document=record.to_doc(), refresh=True)
            return record

        record = DetectorRecord(
            tenant_id=monitor.tenant_id,
            environment=monitor.environment,
            monitor_id=monitor.id,
            ml_job_id=config.job_id,
            datafeed_id=f"datafeed-{config.job_id}",
            detection_mode="auto",
            detector_function=config.detector_function,
            detector_field=config.detector_field,
            index_pattern=config.index_pattern,
            provisioning_state="provisioning",
            availability_state="unknown",
            configured=True,
            created_at=_now(),
            updated_at=_now(),
        )
        self.es.index(index=ML_DETECTOR_INDEX, id=doc_id, document=record.to_doc(), refresh=True)

        try:
            self.ml.ensure_job(config)
            self.ml.start_job(config.job_id)
            record.provisioning_state = "active"
            record.availability_state = "available"
        except Exception as exc:  # ML unavailable / unlicensed / transient
            logger.warning("ML detector provisioning failed for monitor %s: %s", monitor.id, exc)
            record.provisioning_state = "error"
            record.availability_state = "unavailable"
            record.last_error_code = "ml_provisioning_failed"
        record.updated_at = _now()
        self.es.index(index=ML_DETECTOR_INDEX, id=doc_id, document=record.to_doc(), refresh=True)
        return record

    def deregister(self, tenant_id: str, environment: str, monitor_id: str) -> bool:
        """Tear down the ML job for a monitor and mark its record deactivated.

        Idempotent: returns False if no detector record exists. Never raises on an
        already-absent ES job — teardown must not block monitor deletion.
        """
        doc_id = self._doc_id(tenant_id, environment, monitor_id)
        existing = self.get(tenant_id, environment, monitor_id)
        if existing is None:
            return False

        ml_job_id = existing.get("ml_job_id")
        if ml_job_id:
            try:
                self.ml.delete_job(ml_job_id)
            except Exception as exc:
                logger.warning("ML job delete failed for monitor %s (job %s): %s", monitor_id, ml_job_id, exc)

        existing["provisioning_state"] = "deactivated"
        existing["availability_state"] = "unavailable"
        existing["updated_at"] = _now()
        self.es.index(index=ML_DETECTOR_INDEX, id=doc_id, document=existing, refresh=True)
        return True

    def get(self, tenant_id: str, environment: str, monitor_id: str) -> Optional[dict[str, Any]]:
        """Return the detector record for a monitor, or None. Tenant-scoped by doc id."""
        from elasticsearch import NotFoundError

        doc_id = self._doc_id(tenant_id, environment, monitor_id)
        try:
            response = self.es.get(index=ML_DETECTOR_INDEX, id=doc_id)
            return response.get("_source")
        except NotFoundError:
            return None
