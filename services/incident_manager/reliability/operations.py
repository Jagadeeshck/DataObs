"""Deterministic incident staleness and escalation operations.

Consumes response-objective results and deliberately contains no SLO,
error-budget, or burn-rate calculations.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from threading import RLock
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import IncidentObjectiveResult, ObjectiveResultState, ResponseMetricType

MEANINGFUL_PROGRESS_VERSION = "incident-meaningful-progress/1.0.0"
MEANINGFUL_PROGRESS_EVENTS = frozenset(
    {
        "incident_acknowledged",
        "incident_state_transitioned",
        "investigation_evidence_recorded",
        "finding_attached",
        "evidence_attached",
        "mitigation_activity_recorded",
        "approval_decided",
        "remediation_executed",
        "verification_recorded",
        "recovery_signal_recorded",
        "operator_progress_recorded",
    }
)
TERMINAL_INCIDENT_STATES = frozenset({"resolved", "closed"})


class StalenessState(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    CRITICALLY_STALE = "critically_stale"
    UNAVAILABLE = "unavailable"


class EscalationLevel(StrEnum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"


class EscalationTrigger(StrEnum):
    ACKNOWLEDGEMENT_TARGET_BREACHED = "acknowledgement_target_breached"
    INVESTIGATION_TARGET_BREACHED = "investigation_target_breached"
    MITIGATION_TARGET_BREACHED = "mitigation_target_breached"
    RECOVERY_TARGET_BREACHED = "recovery_target_breached"
    RESOLUTION_TARGET_BREACHED = "resolution_target_breached"
    INCIDENT_STALE = "incident_stale"
    INCIDENT_CRITICALLY_STALE = "incident_critically_stale"
    CRITICAL_SEVERITY_UNACKNOWLEDGED = "critical_severity_unacknowledged"
    REOPEN_AFTER_RESOLUTION = "reopen_after_resolution"


class TimelineEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    event_type: str
    occurred_at: datetime
    evidence_ref: str | None = Field(default=None, max_length=500)


class IncidentStalenessPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = "default-staleness"
    version: str = "1.0.0"
    aging_after_seconds: int = Field(default=300, ge=0)
    stale_after_seconds: int = Field(default=900, gt=0)
    critically_stale_after_seconds: int = Field(default=1800, gt=0)
    meaningful_progress_version: str = MEANINGFUL_PROGRESS_VERSION

    @model_validator(mode="after")
    def ordered(self):
        if not self.aging_after_seconds <= self.stale_after_seconds < self.critically_stale_after_seconds:
            raise ValueError("staleness thresholds must be ordered")
        return self


class IncidentOperationalState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    age_ms: int
    age_status: str
    last_meaningful_progress_at: datetime | None
    staleness_duration_ms: int | None
    staleness_state: StalenessState
    policy_id: str
    policy_version: str


class IncidentReliabilityOperationalProjection(BaseModel):
    """Bounded extension layered onto Task 1's objective projection."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    incident_id: str
    current_age_ms: int
    last_meaningful_progress_at: datetime | None
    staleness_duration_ms: int | None
    staleness_state: StalenessState
    active_escalation: bool
    active_escalation_level: EscalationLevel | None = None
    active_escalation_trigger: EscalationTrigger | None = None
    next_response_deadline: datetime | None = None
    time_until_next_deadline_ms: int | None = None
    source_incident_revision: str
    source_reliability_revision: str


class IncidentEscalationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = "default-escalation"
    version: str = "1.0.0"
    level_2_after_seconds: int = Field(default=900, ge=0)
    level_3_after_seconds: int = Field(default=1800, ge=0)
    cooldown_seconds: int = Field(default=300, ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.level_3_after_seconds < self.level_2_after_seconds:
            raise ValueError("level 3 delay must not precede level 2")
        return self


class IncidentEscalationState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    tenant_id: str
    environment: str
    incident_id: str
    active: bool
    current_level: EscalationLevel
    trigger: EscalationTrigger
    triggered_at: datetime
    last_advanced_at: datetime | None = None
    acknowledged_at: datetime | None = None
    cleared_at: datetime | None = None
    clear_reason: str | None = None
    policy_id: str
    policy_version: str
    source_incident_revision: str
    source_reliability_revision: str
    evidence_refs: tuple[str, ...] = Field(default=(), max_length=20)


class IncidentEscalationEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    escalation_id: str
    tenant_id: str
    environment: str
    incident_id: str
    event_type: str
    previous_level: EscalationLevel | None = None
    new_level: EscalationLevel | None = None
    trigger: EscalationTrigger
    occurred_at: datetime
    policy_version: str
    evidence_refs: tuple[str, ...] = Field(default=(), max_length=20)
    reason: str | None = None


def _milliseconds(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() * 1000))


def evaluate_operational_state(
    *,
    opened_at: datetime,
    incident_state: str,
    timeline: Iterable[TimelineEvent],
    now: datetime,
    policy: IncidentStalenessPolicy,
    terminal_at: datetime | None = None,
) -> IncidentOperationalState:
    """Derive age and staleness only from the durable allowlisted timeline."""
    terminal = incident_state.lower() in TERMINAL_INCIDENT_STATES
    progress = [opened_at, *(e.occurred_at for e in timeline if e.event_type in MEANINGFUL_PROGRESS_EVENTS)]
    progress_at = max((value for value in progress if value <= now), default=None)
    if terminal:
        return IncidentOperationalState(
            age_ms=_milliseconds(opened_at, terminal_at or now),
            age_status="stopped",
            last_meaningful_progress_at=progress_at,
            staleness_duration_ms=None,
            staleness_state=StalenessState.FRESH,
            policy_id=policy.id,
            policy_version=policy.version,
        )
    if progress_at is None:
        state, duration = StalenessState.UNAVAILABLE, None
    else:
        duration = _milliseconds(progress_at, now)
        seconds = duration / 1000
        state = (
            StalenessState.CRITICALLY_STALE
            if seconds >= policy.critically_stale_after_seconds
            else (
                StalenessState.STALE
                if seconds >= policy.stale_after_seconds
                else StalenessState.AGING if seconds >= policy.aging_after_seconds else StalenessState.FRESH
            )
        )
    return IncidentOperationalState(
        age_ms=_milliseconds(opened_at, now),
        age_status="active",
        last_meaningful_progress_at=progress_at,
        staleness_duration_ms=duration,
        staleness_state=state,
        policy_id=policy.id,
        policy_version=policy.version,
    )


_OBJECTIVE_TRIGGERS = {
    ResponseMetricType.TIME_TO_ACKNOWLEDGE: EscalationTrigger.ACKNOWLEDGEMENT_TARGET_BREACHED,
    ResponseMetricType.TIME_TO_INVESTIGATION: EscalationTrigger.INVESTIGATION_TARGET_BREACHED,
    ResponseMetricType.TIME_TO_MITIGATION: EscalationTrigger.MITIGATION_TARGET_BREACHED,
    ResponseMetricType.TIME_TO_RECOVERY: EscalationTrigger.RECOVERY_TARGET_BREACHED,
    ResponseMetricType.TIME_TO_RESOLUTION: EscalationTrigger.RESOLUTION_TARGET_BREACHED,
}


def active_triggers(results: Iterable[IncidentObjectiveResult], operational: IncidentOperationalState):
    """Translate Task 1 result states without reevaluating their deadlines."""
    found = {_OBJECTIVE_TRIGGERS[x.metric_type] for x in results if x.state == ObjectiveResultState.BREACHED}
    if operational.staleness_state == StalenessState.CRITICALLY_STALE:
        found.add(EscalationTrigger.INCIDENT_CRITICALLY_STALE)
    elif operational.staleness_state == StalenessState.STALE:
        found.add(EscalationTrigger.INCIDENT_STALE)
    return tuple(sorted(found, key=lambda x: x.value))


def escalation_identity(
    tenant_id: str,
    environment: str,
    incident_id: str,
    trigger: EscalationTrigger,
    level: EscalationLevel,
    policy_version: str,
) -> str:
    return hashlib.sha256(
        "\0".join((tenant_id, environment, incident_id, trigger.value, level.value, policy_version)).encode()
    ).hexdigest()


class IncidentEscalationStore:
    """Atomic reference repository: deterministic create, CAS-like update, durable history contract."""

    def __init__(self):
        self._lock = RLock()
        self._states = {}
        self._events = {}

    def evaluate(
        self,
        *,
        tenant_id: str,
        environment: str,
        incident_id: str,
        triggers: Iterable[EscalationTrigger],
        now: datetime,
        policy: IncidentEscalationPolicy,
        source_incident_revision: str,
        source_reliability_revision: str,
        evidence_refs: tuple[str, ...] = (),
    ):
        active = set(triggers)
        changed = []
        with self._lock:
            scoped = [k for k in self._states if k[:3] == (tenant_id, environment, incident_id)]
            for key in scoped:
                current = self._states[key]
                if current.active and current.trigger not in active:
                    current = current.model_copy(
                        update={"active": False, "cleared_at": now, "clear_reason": "trigger_condition_cleared"}
                    )
                    self._states[key] = current
                    self._event(current, "incident_escalation_cleared", now, reason=current.clear_reason)
                    changed.append(current)
            for trigger in sorted(active, key=lambda x: x.value):
                key = (tenant_id, environment, incident_id, trigger.value)
                current = self._states.get(key)
                if current is None or not current.active:
                    identifier = escalation_identity(
                        tenant_id, environment, incident_id, trigger, EscalationLevel.LEVEL_1, policy.version
                    )
                    current = IncidentEscalationState(
                        id=identifier,
                        tenant_id=tenant_id,
                        environment=environment,
                        incident_id=incident_id,
                        active=True,
                        current_level=EscalationLevel.LEVEL_1,
                        trigger=trigger,
                        triggered_at=now,
                        policy_id=policy.id,
                        policy_version=policy.version,
                        source_incident_revision=source_incident_revision,
                        source_reliability_revision=source_reliability_revision,
                        evidence_refs=evidence_refs,
                    )
                    self._states[key] = current
                    self._event(current, "incident_escalation_triggered", now, new=current.current_level)
                    changed.append(current)
                    continue
                elapsed = (now - current.triggered_at).total_seconds()
                cooldown_elapsed = (now - (current.last_advanced_at or current.triggered_at)).total_seconds()
                desired = current.current_level
                if cooldown_elapsed >= policy.cooldown_seconds:
                    if current.current_level == EscalationLevel.LEVEL_1 and elapsed >= policy.level_2_after_seconds:
                        desired = EscalationLevel.LEVEL_2
                    elif current.current_level == EscalationLevel.LEVEL_2 and elapsed >= policy.level_3_after_seconds:
                        desired = EscalationLevel.LEVEL_3
                if desired != current.current_level:
                    previous = current.current_level
                    current = current.model_copy(
                        update={
                            "current_level": desired,
                            "last_advanced_at": now,
                            "source_incident_revision": source_incident_revision,
                            "source_reliability_revision": source_reliability_revision,
                        }
                    )
                    self._states[key] = current
                    self._event(current, "incident_escalation_advanced", now, previous, desired)
                    changed.append(current)
        return tuple(changed)

    def acknowledge(self, tenant_id, environment, incident_id, escalation_id, *, at):
        with self._lock:
            current = next(
                (
                    v
                    for k, v in self._states.items()
                    if k[:3] == (tenant_id, environment, incident_id) and v.id == escalation_id
                ),
                None,
            )
            if current is None:
                raise KeyError(escalation_id)
            if current.acknowledged_at is not None:
                return current
            updated = current.model_copy(update={"acknowledged_at": at})
            self._states[(tenant_id, environment, incident_id, current.trigger.value)] = updated
            self._event(updated, "incident_escalation_acknowledged", at)
            return updated

    def list(self, tenant_id, environment, incident_id=None):
        with self._lock:
            return tuple(
                v
                for k, v in self._states.items()
                if k[:2] == (tenant_id, environment) and (incident_id is None or k[2] == incident_id)
            )

    def events(self, tenant_id, environment, incident_id):
        with self._lock:
            return tuple(
                v
                for v in self._events.values()
                if (v.tenant_id, v.environment, v.incident_id) == (tenant_id, environment, incident_id)
            )

    def _event(self, state, event_type, at, previous=None, new=None, reason=None):
        event_id = hashlib.sha256(f"{state.id}\0{event_type}\0{at.isoformat()}\0{new or ''}".encode()).hexdigest()
        self._events.setdefault(
            event_id,
            IncidentEscalationEvent(
                id=event_id,
                escalation_id=state.id,
                tenant_id=state.tenant_id,
                environment=state.environment,
                incident_id=state.incident_id,
                event_type=event_type,
                previous_level=previous,
                new_level=new,
                trigger=state.trigger,
                occurred_at=at,
                policy_version=state.policy_version,
                evidence_refs=state.evidence_refs,
                reason=reason,
            ),
        )
