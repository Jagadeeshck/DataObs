"""Six-pillar DataObs product model and scoring utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List


class Pillar(str, Enum):
    """Canonical DataObs observability pillars emitted by product APIs."""

    PLATFORM = "platform"
    DATA_PIPELINE = "data_pipeline"
    DATA = "data"
    FINOPS_COST = "finops_cost"
    BUSINESS = "business"
    AI_AGENT = "ai_agent"


LEGACY_PILLAR_ALIASES: Dict[str, Pillar] = {
    "full_stack": Pillar.PLATFORM,
    "pipeline": Pillar.DATA_PIPELINE,
    "data": Pillar.DATA,
    "business": Pillar.BUSINESS,
}


def parse_pillar(value: str | Pillar) -> Pillar:
    """Parse canonical and deprecated pillar values, returning canonical values."""

    if isinstance(value, Pillar):
        return value
    normalized = value.strip().lower().replace("-", "_")
    if normalized in LEGACY_PILLAR_ALIASES:
        return LEGACY_PILLAR_ALIASES[normalized]
    return Pillar(normalized)


def canonical_pillar_value(value: str | Pillar) -> str:
    """Return the canonical wire value for API/config responses."""

    return parse_pillar(value).value


def pillar_deprecation(value: str | Pillar) -> dict[str, str] | None:
    """Return deprecation metadata for legacy pillar inputs."""

    if isinstance(value, Pillar):
        return None
    normalized = value.strip().lower().replace("-", "_")
    replacement = LEGACY_PILLAR_ALIASES.get(normalized)
    if replacement is None or normalized == replacement.value:
        return None
    return {"deprecated": normalized, "replacement": replacement.value}


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    description: str
    default_weight: float = 1.0


@dataclass
class PillarDefinition:
    pillar: Pillar
    name: str
    question: str
    capabilities: List[Capability] = field(default_factory=list)

    def capability_index(self) -> Dict[str, Capability]:
        return {capability.key: capability for capability in self.capabilities}


@dataclass
class CapabilityStatus:
    key: str
    implemented: bool
    maturity: float


@dataclass
class PillarScore:
    pillar: Pillar
    score: float
    max_score: float
    implemented_capabilities: int
    total_capabilities: int

    @property
    def percentage(self) -> float:
        return 0.0 if self.max_score == 0 else (self.score / self.max_score) * 100


PILLAR_REGISTRY: Dict[Pillar, PillarDefinition] = {
    Pillar.PLATFORM: PillarDefinition(
        Pillar.PLATFORM,
        "Platform Observability",
        "What is deployed, where, and is it healthy?",
        [
            Capability(
                "infrastructure_inventory",
                "Infrastructure Inventory",
                "Infrastructure, host, container, and Kubernetes inventory.",
            ),
            Capability(
                "runtime_telemetry",
                "Runtime Telemetry",
                "Metrics, logs, traces, dependency topology, saturation, and capacity.",
            ),
            Capability(
                "lifecycle_visibility", "Lifecycle Visibility", "Version, cloud service health, and lifecycle status."
            ),
        ],
    ),
    Pillar.DATA_PIPELINE: PillarDefinition(
        Pillar.DATA_PIPELINE,
        "Data Pipeline and Job Observability",
        "Are pipelines and jobs running correctly and on time?",
        [
            Capability("job_health", "Job Health", "Job health, failures, retries, and run comparison."),
            Capability(
                "sla_adherence", "SLA Adherence", "Schedules, SLA adherence, and deployment/change correlation."
            ),
            Capability("pipeline_latency", "Pipeline Latency", "Throughput, stream lag, and pipeline latency."),
        ],
    ),
    Pillar.DATA: PillarDefinition(
        Pillar.DATA,
        "Data Observability",
        "Can consumers trust the data?",
        [
            Capability("freshness", "Freshness", "Dataset freshness and volume state.", 1.2),
            Capability(
                "validation", "Validation", "Schema, quality, nullness, uniqueness, cardinality, and drift checks."
            ),
            Capability("lineage", "Lineage", "Dataset and column lineage, data contracts, and blast radius.", 1.2),
        ],
    ),
    Pillar.FINOPS_COST: PillarDefinition(
        Pillar.FINOPS_COST,
        "FinOps and Cost Observability",
        "What is the platform costing, and why?",
        [
            Capability("cost_allocation", "Cost Allocation", "Cost by tenant, team, job, dataset, and service."),
            Capability("unit_economics", "Unit Economics", "Storage, retention, unit economics, and forecasts."),
            Capability(
                "cost_optimization", "Cost Optimization", "Idle-resource detection, anomalies, and recommendations."
            ),
        ],
    ),
    Pillar.BUSINESS: PillarDefinition(
        Pillar.BUSINESS,
        "Business Observability",
        "Is the platform delivering business value?",
        [
            Capability("adoption", "Adoption", "Adoption, tenant health, and business KPIs."),
            Capability("slo_attainment", "SLO Attainment", "SLA/SLO attainment, time-to-data, and reliability."),
            Capability(
                "executive_scorecards", "Executive Scorecards", "Incident business impact and executive scorecards."
            ),
        ],
    ),
    Pillar.AI_AGENT: PillarDefinition(
        Pillar.AI_AGENT,
        "AI and Agent Observability",
        "Can AI models and autonomous agents be trusted, controlled, and audited?",
        [
            Capability(
                "agent_inventory",
                "Model and Agent Inventory",
                "Inventory, prompts, tool calls, token cost, and latency.",
            ),
            Capability("evaluation", "Quality and Evaluation", "Quality, grounding evidence, and policy violations."),
            Capability("action_audit", "Action Audit", "Action audit trail, approvals, rollback, and verification."),
        ],
    ),
}


def score_pillar(pillar: Pillar | str, statuses: Iterable[CapabilityStatus]) -> PillarScore:
    definition = PILLAR_REGISTRY[parse_pillar(pillar)]
    status_map = {status.key: status for status in statuses}
    score = max_score = 0.0
    implemented = 0
    for capability in definition.capabilities:
        max_score += capability.default_weight
        status = status_map.get(capability.key)
        if status:
            implemented += int(status.implemented)
            score += max(0.0, min(status.maturity, 1.0)) * capability.default_weight
    return PillarScore(definition.pillar, score, max_score, implemented, len(definition.capabilities))


def score_all_pillars(statuses_by_pillar: Dict[Pillar | str, Iterable[CapabilityStatus]]) -> List[PillarScore]:
    normalized = {parse_pillar(pillar): statuses for pillar, statuses in statuses_by_pillar.items()}
    return [score_pillar(pillar, normalized.get(pillar, [])) for pillar in Pillar]
