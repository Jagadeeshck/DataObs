"""Pure six-pillar aggregation logic for the Command Center summary.

No Elasticsearch here — inputs are plain lists of per-pillar read-model documents,
output is the summary dict the Console reads. This keeps the health-rollup and
priority-queue rules deterministic and unit-testable.

Canonical six pillars (product vision):
  platform, data_pipeline, data, finops_cost, business, ai_agent

v1 computes health for the three implemented pillars (platform, data_pipeline, data)
from real read-models. The three future pillars are reported as `unknown` with an
explicit "not yet collected" coverage note — never fabricated as healthy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

# Canonical pillar order and display names.
PILLARS: tuple[tuple[str, str], ...] = (
    ("platform", "Platform Observability"),
    ("data_pipeline", "Data Pipeline Observability"),
    ("data", "Data Observability"),
    ("finops_cost", "FinOps & Cost"),
    ("business", "Business Observability"),
    ("ai_agent", "AI & Agent Observability"),
)

# Pillars without a collection path yet. Reported unknown, not healthy.
_FUTURE_PILLARS = {"finops_cost", "business", "ai_agent"}

_SEVERITY_RANK = {"critical": 3, "high": 2, "warning": 1, "medium": 1, "low": 0, "info": 0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _worst_health(states: Iterable[str]) -> str:
    """Return the worst health across states, or 'unknown' if none are known."""
    order = ["critical", "degraded", "warning", "healthy"]
    known = [s for s in states if s in order]
    if not known:
        return "unknown"
    for level in order:
        if level in known:
            return level
    return "unknown"


def _health_from_counts(total: int, unhealthy: int) -> str:
    """Derive a pillar health band from observed counts (total observed, unhealthy)."""
    if total == 0:
        # Observed estate is empty — a real measured zero, reported healthy only when
        # we genuinely observed and found nothing wrong.
        return "healthy"
    ratio = unhealthy / total
    if ratio == 0:
        return "healthy"
    if ratio < 0.1:
        return "warning"
    if ratio < 0.3:
        return "degraded"
    return "critical"


def _pillar(
    pillar_id: str,
    name: str,
    *,
    observed: bool,
    total: int = 0,
    unhealthy: int = 0,
    metric: str | None = None,
    coverage: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    if not observed:
        return {
            "id": pillar_id,
            "name": name,
            "health": "unknown",
            "metric": None,
            "trend": None,
            "coverage": coverage or "Not yet collected",
            "issues": None,
            "observed_at": None,
        }
    return {
        "id": pillar_id,
        "name": name,
        "health": _health_from_counts(total, unhealthy),
        "metric": metric,
        "trend": None,
        "coverage": coverage,
        "issues": unhealthy,
        "observed_at": observed_at or _now(),
    }


def _incident_priority_items(incidents: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    """Project open incidents into the Console priority-queue shape, worst first."""
    items: list[dict[str, Any]] = []
    for inc in incidents:
        state = str(inc.get("state", "")).lower()
        if state in {"resolved", "closed"}:
            continue
        severity = str(inc.get("severity", "warning")).lower()
        items.append(
            {
                "id": inc.get("incident_id") or inc.get("id") or inc.get("_id", "unknown"),
                "problem": inc.get("title") or inc.get("summary") or "Open incident",
                "entity": inc.get("primary_resource") or inc.get("primary_entity") or inc.get("entity") or "unknown",
                "service": inc.get("pillar") or inc.get("service") or "data",
                "owner": inc.get("owner") or inc.get("assignee"),
                "started": inc.get("opened_at") or inc.get("created_at"),
                "severity": severity,
                "impact": inc.get("impact_summary") or inc.get("impact"),
                "automation": inc.get("notification_state") or inc.get("automation_status"),
            }
        )
    items.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"], 0), reverse=True)
    return items[:limit]


def aggregate_summary(
    tenant_id: str,
    environment: str,
    *,
    incidents: list[dict[str, Any]] | None = None,
    quality: list[dict[str, Any]] | None = None,
    freshness: list[dict[str, Any]] | None = None,
    lineage: list[dict[str, Any]] | None = None,
    streams: list[dict[str, Any]] | None = None,
    sources_available: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute the six-pillar Command Center summary from per-pillar read-models.

    Each ``*`` list is the current read-model docs for that pillar. ``sources_available``
    marks which sources actually answered; a source that errored/was absent makes the
    summary ``complete=False`` and leaves its pillar ``unknown`` rather than healthy.
    """
    incidents = incidents or []
    quality = quality or []
    freshness = freshness or []
    lineage = lineage or []
    streams = streams or []
    availability = sources_available or {}

    now = _now()

    # ── Data pillar: quality + freshness ────────────────────────────────────
    data_observed = availability.get("quality", bool(quality)) or availability.get("freshness", bool(freshness))
    quality_total = len(quality)
    quality_bad = sum(1 for q in quality if str(q.get("status", "")).lower() in {"fail", "failing", "breached"})
    freshness_bad = sum(1 for f in freshness if str(f.get("status", "")).lower() in {"stale", "breached", "late"})
    data_total = quality_total + len(freshness)
    data_bad = quality_bad + freshness_bad
    data_pillar = _pillar(
        "data",
        "Data Observability",
        observed=data_observed,
        total=data_total,
        unhealthy=data_bad,
        metric=f"{quality_total} checks · {len(freshness)} freshness",
        coverage=f"{data_total} monitored assets" if data_total else "0 observed",
        observed_at=now,
    )

    # ── Data Pipeline pillar: lineage + stream health ───────────────────────
    pipeline_observed = availability.get("lineage", bool(lineage)) or availability.get("streams", bool(streams))
    stream_bad = sum(
        1
        for s in streams
        if str(s.get("status", s.get("health_state", s.get("health", "")))).lower()
        in {"critical", "degraded", "breaching"}
    )
    pipeline_total = len(lineage) + len(streams)
    pipeline_pillar = _pillar(
        "data_pipeline",
        "Data Pipeline Observability",
        observed=pipeline_observed,
        total=pipeline_total,
        unhealthy=stream_bad,
        metric=f"{len(streams)} streams · {len(lineage)} lineage edges",
        coverage=f"{pipeline_total} pipeline entities" if pipeline_total else "0 observed",
        observed_at=now,
    )

    # ── Platform pillar: stream clusters / infra signals ────────────────────
    platform_observed = availability.get("streams", bool(streams))
    cluster_bad = sum(
        1
        for s in streams
        if str(s.get("status", s.get("health_state", s.get("cluster_health", "")))).lower() in {"critical", "degraded"}
    )
    platform_pillar = _pillar(
        "platform",
        "Platform Observability",
        observed=platform_observed,
        total=len(streams),
        unhealthy=cluster_bad,
        metric=f"{len(streams)} platform resources",
        coverage=f"{len(streams)} resources" if streams else "0 observed",
        observed_at=now,
    )

    future_pillars = [_pillar(pid, name, observed=False) for pid, name in PILLARS if pid in _FUTURE_PILLARS]

    pillars = [platform_pillar, pipeline_pillar, data_pillar, *future_pillars]

    priority_items = _incident_priority_items(incidents)
    critical_incidents = sum(1 for i in priority_items if i["severity"] == "critical")
    affected_services = len({i["entity"] for i in priority_items if i["entity"] != "unknown"})

    # Overall health: worst of the observed pillars; unknown pillars don't count as healthy.
    overall = _worst_health(p["health"] for p in pillars)

    missing_sources = [name for name, ok in availability.items() if not ok] if availability else []
    expected_sources = {"incidents", "quality", "freshness", "lineage", "streams"}
    answered = {name for name, ok in availability.items() if ok} if availability else set()
    complete = expected_sources.issubset(answered)
    warnings: list[str] = []
    if not complete:
        absent = sorted(expected_sources - answered)
        warnings.append("Partial pillar coverage; sources not answering: " + ", ".join(absent))

    observed_count = sum(1 for name in expected_sources if availability.get(name))
    source_coverage = round(observed_count / len(expected_sources) * 100) if availability else None

    return {
        "@timestamp": now,
        "tenant_id": tenant_id,
        "environment": environment,
        "overall_health": overall,
        "critical_incidents": critical_incidents,
        "affected_services": affected_services,
        "pillars": pillars,
        "priority_items": priority_items,
        "recent_changes": [],
        "data_status": {
            "complete": complete,
            "warnings": warnings,
            "sources": sorted(answered) if availability else [],
            "missing_inputs": missing_sources,
            "source_coverage": source_coverage,
            "observed_at": now,
        },
    }
