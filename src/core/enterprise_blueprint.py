"""Enterprise readiness blueprint helpers for competitive data observability positioning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set


@dataclass(frozen=True)
class BlueprintCapability:
    """Commercially relevant capability mapped to contract outcomes."""

    key: str
    title: str
    why_it_wins_contracts: str
    implementation_hint: str
    business_value_score: int  # 1-5
    implementation_effort_score: int  # 1-5 (lower is easier)

    @property
    def priority_score(self) -> float:
        """Higher means better near-term return for enterprise programs."""

        return self.business_value_score / max(1, self.implementation_effort_score)


BLUEPRINT_CAPABILITIES: List[BlueprintCapability] = [
    BlueprintCapability(
        key="data_product_slos",
        title="Data Product SLOs and Reliability Scorecards",
        why_it_wins_contracts=(
            "Executives can approve programs faster when reliability targets are clear for each "
            "dashboard, API, and AI use case."
        ),
        implementation_hint=(
            "Bundle freshness, quality, and schema indicators into SLI/SLO scorecards and publish "
            "monthly error-budget reports."
        ),
        business_value_score=5,
        implementation_effort_score=2,
    ),
    BlueprintCapability(
        key="incident_triage_workbench",
        title="Lineage-Aware Incident Triage Workbench",
        why_it_wins_contracts=(
            "Large enterprises buy faster when MTTR drops and ownership is clear across domain teams."
        ),
        implementation_hint=(
            "Auto-attach upstream/downstream blast radius, suspected owners, and runbooks to incidents."
        ),
        business_value_score=5,
        implementation_effort_score=3,
    ),
    BlueprintCapability(
        key="policy_guardrails",
        title="Policy-Aware AI and Access Guardrails",
        why_it_wins_contracts=(
            "Security and governance stakeholders sign off more quickly when automation is auditable and RBAC-aware."
        ),
        implementation_hint=(
            "Record policy checks, approvals, and AI recommendation traces before remediation actions are allowed."
        ),
        business_value_score=4,
        implementation_effort_score=3,
    ),
    BlueprintCapability(
        key="monitor_bootstrap",
        title="No-Code Monitor Bootstrap Templates",
        why_it_wins_contracts=(
            "Shorter onboarding timelines make pilot-to-production conversions easier for consulting engagements."
        ),
        implementation_hint=(
            "Provide starter packs by domain (finance, retail, healthcare) with prewired checks and alert policies."
        ),
        business_value_score=4,
        implementation_effort_score=2,
    ),
    BlueprintCapability(
        key="finops_visibility",
        title="Pipeline Cost and FinOps Visibility",
        why_it_wins_contracts=("Procurement teams prioritize vendors that reduce both data incidents and cloud spend."),
        implementation_hint=(
            "Correlate failed pipelines and quality regressions with warehouse/job costs in one dashboard."
        ),
        business_value_score=4,
        implementation_effort_score=4,
    ),
]


def _normalize_implemented_keys(implemented_keys: Iterable[str]) -> Set[str]:
    return {key.strip().lower() for key in implemented_keys if key and key.strip()}


def enterprise_backlog(implemented_keys: Iterable[str]) -> List[dict]:
    """Return a prioritized delivery backlog for enterprise contract pursuits."""

    implemented = _normalize_implemented_keys(implemented_keys)
    items: List[dict] = []

    for capability in BLUEPRINT_CAPABILITIES:
        if capability.key in implemented:
            continue
        items.append(
            {
                "key": capability.key,
                "title": capability.title,
                "why_it_wins_contracts": capability.why_it_wins_contracts,
                "implementation_hint": capability.implementation_hint,
                "business_value_score": capability.business_value_score,
                "implementation_effort_score": capability.implementation_effort_score,
                "priority_score": round(capability.priority_score, 2),
            }
        )

    return sorted(
        items,
        key=lambda item: (item["priority_score"], item["business_value_score"]),
        reverse=True,
    )
