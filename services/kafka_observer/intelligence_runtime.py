"""Fenced, persistence-ordered Stream Intelligence evaluation runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from packages.streaming.intelligence import (
    AnomalyEvaluation,
    DetectorDefinition,
    DetectorState,
    EvidenceSeries,
    ExpectedRange,
    evaluate_anomaly,
)
from services.kafka_observer.intelligence_repository import canonical_id
from services.kafka_observer.reliability_runtime import StaleWriter


@dataclass
class IntelligenceRuntimeHealth:
    configured: bool = True
    worker_id: str = ""
    worker_version: str = "v1"
    lease_status: str = "idle"
    fencing_token: int | None = None
    lease_expiry: datetime | None = None
    last_heartbeat: datetime | None = None
    latest_cycle_start: datetime | None = None
    latest_cycle_finish: datetime | None = None
    detectors_due: int = 0
    detectors_evaluated: int = 0
    detectors_skipped: int = 0
    detectors_failed: int = 0
    insufficient_data_count: int = 0
    anomaly_count: int = 0
    severe_count: int = 0
    forecasts_produced: int = 0
    failure_candidates_produced: int = 0
    pending_reconciliations: int = 0
    pending_signals: int = 0
    elasticsearch_dependency: str = "unknown"
    latest_successful_evaluation: datetime | None = None
    latest_failed_evaluation: datetime | None = None
    consecutive_runtime_failures: int = 0
    lease_renewal_failures: int = 0


class IntelligenceRuntime:
    MAX_BATCH = 200

    def __init__(
        self,
        repository: object,
        observer: Callable[..., EvidenceSeries],
        worker_id: str,
        *,
        lease_seconds: int = 90,
        freshness_seconds: int = 300,
    ):
        self.repository = repository
        self.observer = observer
        self.lease_seconds = max(15, lease_seconds)
        self.freshness_seconds = max(1, freshness_seconds)
        self.health = IntelligenceRuntimeHealth(worker_id=worker_id)
        self.stopping = False

    def stop(self) -> None:
        self.stopping = True

    @staticmethod
    def _stale(evaluation: AnomalyEvaluation) -> AnomalyEvaluation:
        return AnomalyEvaluation(
            DetectorState.STALE,
            evaluation.method,
            None,
            evaluation.expected_value,
            evaluation.expected_range,
            None,
            evaluation.sample_count,
            evaluation.data_coverage,
            0,
            0,
            ("latest_evidence_stale",),
        )

    def run_once(
        self, tenant: str, environment: str, now: datetime | None = None, *, limit: int = MAX_BATCH
    ) -> list[dict[str, object]]:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        scope_limit = min(max(limit, 1), self.MAX_BATCH)
        self.health.latest_cycle_start = now
        expiry = now + timedelta(seconds=self.lease_seconds)
        token = self.repository.acquire_lease(tenant, environment, self.health.worker_id, expiry)
        if token is None:
            self.health.lease_status = "contended"
            return []
        self.health.lease_status, self.health.fencing_token, self.health.lease_expiry = "held", token, expiry
        self.health.elasticsearch_dependency = "available"
        definitions = self.repository.list_due_detectors(tenant, environment, now, scope_limit)
        self.health.detectors_due = len(definitions)
        completed: list[dict[str, object]] = []
        for definition in definitions:
            if self.stopping:
                self.health.detectors_skipped += 1
                break
            try:
                clock = datetime.now(timezone.utc)
                if clock >= expiry - timedelta(seconds=self.lease_seconds * 0.4):
                    expiry = clock + timedelta(seconds=self.lease_seconds)
                    try:
                        self.repository.renew_lease(tenant, environment, self.health.worker_id, token, expiry)
                        self.health.lease_expiry = expiry
                    except Exception:
                        self.health.lease_renewal_failures += 1
                        raise
                self.repository.validate_fencing_token(tenant, environment, token, self.health.worker_id)
                previous = self.repository.load_previous_state(definition)
                start = now - timedelta(seconds=definition.baseline_window_seconds)
                series = self.observer(definition, start, now)
                evaluation = evaluate_anomaly(definition, series, previous)
                measured = [point for point in series.points if point.value is not None]
                if measured and now - measured[-1].timestamp.astimezone(timezone.utc) > timedelta(
                    seconds=self.freshness_seconds
                ):
                    evaluation = self._stale(evaluation)
                evaluation_id = canonical_id(
                    "evaluation-run",
                    tenant,
                    environment,
                    definition.resource_type,
                    definition.resource_id,
                    definition.detector_id,
                    now.isoformat(),
                )
                document = self._document(definition, evaluation, previous.state, evaluation_id, now, series)
                # Immutable evidence is the reconciliation anchor. Checkpointing is last.
                self.repository.append_evaluation(definition, evaluation_id, document, token)
                self.repository.update_anomaly_projection(definition, document, token)
                self._signal(definition, document, previous.state, evaluation.state, token)
                self.repository.advance_detector_checkpoint(
                    definition, evaluation_id, now + timedelta(seconds=definition.evaluation_interval_seconds), token
                )
                completed.append(document)
                self.health.detectors_evaluated += 1
                self.health.latest_successful_evaluation = now
                self.health.consecutive_runtime_failures = 0
                self.health.insufficient_data_count += evaluation.state == DetectorState.INSUFFICIENT_DATA
                self.health.anomaly_count += evaluation.state == DetectorState.ANOMALOUS
                self.health.severe_count += evaluation.state == DetectorState.SEVERE
            except StaleWriter:
                self.health.lease_status = "lost"
                raise
            except Exception:
                self.health.detectors_failed += 1
                self.health.pending_reconciliations += 1
                self.health.latest_failed_evaluation = now
                self.health.consecutive_runtime_failures += 1
        self.health.latest_cycle_finish = self.health.last_heartbeat = now
        self.repository.persist_runtime_health(tenant, environment, asdict(self.health), token)
        return completed

    @staticmethod
    def _document(
        definition: DetectorDefinition,
        evaluation: AnomalyEvaluation,
        previous: DetectorState,
        evaluation_id: str,
        now: datetime,
        series: EvidenceSeries,
    ) -> dict[str, object]:
        expected: ExpectedRange | None = evaluation.expected_range
        evidence_refs = [point.evidence_reference for point in series.points if point.evidence_reference][-100:]
        return {
            "evaluation_id": evaluation_id,
            "detector_id": definition.detector_id,
            "tenant_id": definition.tenant_id,
            "environment": definition.environment,
            "resource_type": definition.resource_type,
            "resource_id": definition.resource_id,
            "metric": definition.metric,
            "previous_state": previous.value,
            "state": evaluation.state.value,
            "observed_value": evaluation.observed_value,
            "expected_value": evaluation.expected_value,
            "range_lower": expected.lower if expected else None,
            "range_upper": expected.upper if expected else None,
            "deviation_score": evaluation.deviation_score,
            "method": evaluation.method,
            "sample_count": evaluation.sample_count,
            "confidence": min(1.0, evaluation.data_coverage),
            "data_coverage": evaluation.data_coverage,
            "consecutive_anomalies": evaluation.consecutive_anomalies,
            "consecutive_recoveries": evaluation.consecutive_recoveries,
            "reason_codes": list(evaluation.reason_codes),
            "evidence_references": evidence_refs,
            "evaluated_at": now,
            "@timestamp": now,
            "schema_version": "v1",
        }

    def _signal(
        self,
        definition: DetectorDefinition,
        document: dict[str, object],
        previous: DetectorState,
        current: DetectorState,
        token: int,
    ) -> None:
        transitions = {
            DetectorState.ANOMALOUS: "anomaly_confirmed",
            DetectorState.SEVERE: "anomaly_severe",
            DetectorState.RECOVERING: "anomaly_recovering",
            DetectorState.NORMAL: "anomaly_recovered",
        }
        event = transitions.get(current)
        if (
            not event
            or current == previous
            or (
                current == DetectorState.NORMAL
                and previous not in {DetectorState.RECOVERING, DetectorState.ANOMALOUS, DetectorState.SEVERE}
            )
        ):
            return
        # The evaluation time bucket bounds repeat notifications while retaining deterministic replay.
        evaluated = document["evaluated_at"]
        signal_id = canonical_id(
            "transition",
            definition.tenant_id,
            definition.environment,
            definition.resource_type,
            definition.resource_id,
            definition.detector_id,
            event,
            str(evaluated)[:13],
        )
        signal = dict(document) | {"signal_id": signal_id, "signal_type": event, "current_state": current.value}
        self.repository.persist_signal(definition, signal_id, signal, token)
