"""DataObs pillar model and scoring utilities.

This module defines a product-level abstraction for the four DataObs observability
pillars and provides a lightweight scorecard engine that can be used by APIs,
CLI commands, and dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List


class Pillar(str, Enum):
    """Top-level DataObs observability pillars."""

    FULL_STACK = "full_stack"
    PIPELINE = "pipeline"
    DATA = "data"
    BUSINESS = "business"


@dataclass(frozen=True)
class Capability:
    """A capability implemented inside a pillar."""

    key: str
    name: str
    description: str
    default_weight: float = 1.0


@dataclass
class PillarDefinition:
    """Definition of a pillar and its required capabilities."""

    pillar: Pillar
    question: str
    capabilities: List[Capability] = field(default_factory=list)

    def capability_index(self) -> Dict[str, Capability]:
        return {capability.key: capability for capability in self.capabilities}


@dataclass
class CapabilityStatus:
    """Runtime state for a capability."""

    key: str
    implemented: bool
    maturity: float  # 0.0 -> 1.0


@dataclass
class PillarScore:
    """Computed score for one pillar."""

    pillar: Pillar
    score: float
    max_score: float
    implemented_capabilities: int
    total_capabilities: int

    @property
    def percentage(self) -> float:
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


PILLAR_REGISTRY: Dict[Pillar, PillarDefinition] = {
    Pillar.FULL_STACK: PillarDefinition(
        pillar=Pillar.FULL_STACK,
        question="What is happening in the runtime stack right now?",
        capabilities=[
            Capability("infra_metrics", "Infrastructure Metrics", "Host/container/Kubernetes health and saturation."),
            Capability("apm_traces", "APM Tracing", "Distributed tracing with OpenTelemetry span context."),
            Capability("log_analytics", "Log Analytics", "Centralized logs with anomaly detection on error patterns."),
        ],
    ),
    Pillar.PIPELINE: PillarDefinition(
        pillar=Pillar.PIPELINE,
        question="Are pipelines meeting expected SLAs and contracts?",
        capabilities=[
            Capability("job_sla", "Job SLA", "Schedule adherence, delays, retries, and cost visibility."),
            Capability("stream_health", "Stream Health", "Lag/throughput/consumer-group health for streaming systems."),
            Capability("deployment_obs", "Deployment Observability", "CI/CD and release quality for data workloads."),
        ],
    ),
    Pillar.DATA: PillarDefinition(
        pillar=Pillar.DATA,
        question="Can consumers trust this data for decisions?",
        capabilities=[
            Capability("freshness", "Freshness", "How stale is each critical dataset?", default_weight=1.2),
            Capability("validation", "Validation", "Schema, null, uniqueness, range, and referential integrity checks."),
            Capability("lineage", "Lineage", "End-to-end source to consumer lineage with impact analysis.", default_weight=1.2),
        ],
    ),
    Pillar.BUSINESS: PillarDefinition(
        pillar=Pillar.BUSINESS,
        question="What is the business impact of incidents and data drift?",
        capabilities=[
            Capability("kpi_correlation", "KPI Correlation", "Link data incidents to KPI movement and revenue impact."),
            Capability("executive_views", "Executive Views", "Role-based dashboards and service-level scorecards."),
            Capability("incident_cost", "Incident Cost", "Estimated dollar/time impact for prioritization."),
        ],
    ),
}


def score_pillar(pillar: Pillar, statuses: Iterable[CapabilityStatus]) -> PillarScore:
    """Compute weighted implementation score for a single pillar."""

    definition = PILLAR_REGISTRY[pillar]
    status_map = {status.key: status for status in statuses}

    score = 0.0
    max_score = 0.0
    implemented = 0

    for capability in definition.capabilities:
        max_score += capability.default_weight
        status = status_map.get(capability.key)
        if not status:
            continue
        if status.implemented:
            implemented += 1
        bounded_maturity = max(0.0, min(status.maturity, 1.0))
        score += bounded_maturity * capability.default_weight

    return PillarScore(
        pillar=pillar,
        score=score,
        max_score=max_score,
        implemented_capabilities=implemented,
        total_capabilities=len(definition.capabilities),
    )


def score_all_pillars(statuses_by_pillar: Dict[Pillar, Iterable[CapabilityStatus]]) -> List[PillarScore]:
    """Compute scorecards across the full product strategy."""

    return [
        score_pillar(pillar, statuses_by_pillar.get(pillar, []))
        for pillar in Pillar
    ]
