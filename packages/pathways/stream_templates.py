"""Stream detector template descriptors for pathway authoring.

These are *authoring presets* only: each template pre-fills a safe, honest set of
``DetectorDefinition`` fields for common stream concerns (freshness, lag,
throughput). Templates never fabricate measurements and never claim a metric is
supported unless the (resource_type, metric, method, direction) tuple is backed by
``packages.streaming.intelligence.CAPABILITIES`` / ``METHODS``. A template is a
starting point a user can edit; it is not a running detector.

Honesty semantics preserved:
- A template describes *intended* evaluation, not an observed value. It carries no
  measured/zero data.
- ``applicable`` is ``True`` only when the backing capability tuple is valid, so an
  unsupported combination is surfaced as ``unknown`` capability rather than a
  silent zero or a false claim of support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from packages.streaming.intelligence import CAPABILITIES, METHODS, Direction

__all__ = ["StreamDetectorTemplate", "STREAM_DETECTOR_TEMPLATES", "list_templates", "get_template"]


@dataclass(frozen=True)
class StreamDetectorTemplate:
    """A bounded, editable preset for creating a stream detector."""

    template_id: str
    title: str
    category: str  # freshness | lag | throughput
    description: str
    resource_type: str
    metric: str
    method: str
    direction: Direction
    baseline_window_seconds: int
    evaluation_window_seconds: int
    evaluation_interval_seconds: int
    minimum_sample_count: int = 8
    sensitivity: float = 3.5
    seasonal_mode: str = "none"
    rationale: str = ""

    @property
    def applicable(self) -> bool:
        """True only when the backing capability + method + direction are real."""
        capability = CAPABILITIES.get(self.resource_type)
        return (
            capability is not None
            and self.metric in capability
            and self.method in METHODS
            and self.direction in {"high", "low", "both"}
        )

    @property
    def capability_status(self) -> str:
        """Distinguish a supported preset from one whose capability is unknown."""
        return "supported" if self.applicable else "unknown"

    def detector_fields(self) -> dict[str, Any]:
        """Return the editable detector fields this template pre-fills.

        The caller supplies tenant/environment/resource_id/actor; a template never
        injects identity or persistence state.
        """
        return {
            "resource_type": self.resource_type,
            "metric": self.metric,
            "method": self.method,
            "direction": self.direction,
            "baseline_window_seconds": self.baseline_window_seconds,
            "evaluation_window_seconds": self.evaluation_window_seconds,
            "evaluation_interval_seconds": self.evaluation_interval_seconds,
            "minimum_sample_count": self.minimum_sample_count,
            "sensitivity": self.sensitivity,
            "seasonal_mode": self.seasonal_mode,
        }

    def descriptor(self) -> dict[str, Any]:
        """Serialisable descriptor for the authoring picker."""
        return {
            "template_id": self.template_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "rationale": self.rationale,
            "capability_status": self.capability_status,
            "applicable": self.applicable,
            "detector_fields": self.detector_fields(),
        }


# Presets cover the three authoring concerns the brief names: freshness, lag,
# throughput. Each tuple is validated against CAPABILITIES/METHODS at import-check
# time via the applicable guard and the backend self-check test.
STREAM_DETECTOR_TEMPLATES: tuple[StreamDetectorTemplate, ...] = (
    StreamDetectorTemplate(
        template_id="freshness_cluster_observation",
        title="Cluster observation freshness",
        category="freshness",
        description="Flag when a Kafka cluster stops reporting fresh observations.",
        resource_type="kafka_cluster",
        metric="observation_freshness",
        method="relative_change",
        direction="high",
        baseline_window_seconds=86_400,
        evaluation_window_seconds=900,
        evaluation_interval_seconds=300,
        rationale="Rising observation age indicates stale or missing telemetry, not a healthy zero.",
    ),
    StreamDetectorTemplate(
        template_id="freshness_consumer_group",
        title="Consumer group freshness",
        category="freshness",
        description="Detect degraded offset-reporting freshness for a consumer group.",
        resource_type="consumer_group",
        metric="observation_freshness",
        method="relative_change",
        direction="high",
        baseline_window_seconds=86_400,
        evaluation_window_seconds=900,
        evaluation_interval_seconds=300,
        rationale="Stale offset reporting must be surfaced as unknown rather than treated as caught-up.",
    ),
    StreamDetectorTemplate(
        template_id="lag_consumer_total",
        title="Consumer total lag anomaly",
        category="lag",
        description="Detect abnormal growth in a consumer group's total lag.",
        resource_type="consumer_group",
        metric="total_lag",
        method="robust_zscore",
        direction="high",
        baseline_window_seconds=86_400,
        evaluation_window_seconds=1_800,
        evaluation_interval_seconds=300,
        sensitivity=4.0,
        rationale="Robust z-score tolerates spiky lag while still catching sustained backlog growth.",
    ),
    StreamDetectorTemplate(
        template_id="lag_consumer_growth_rate",
        title="Consumer lag growth rate",
        category="lag",
        description="Detect a sustained upward rate of change in consumer lag.",
        resource_type="consumer_group",
        metric="lag_growth",
        method="rate_of_change",
        direction="high",
        baseline_window_seconds=43_200,
        evaluation_window_seconds=1_800,
        evaluation_interval_seconds=300,
        rationale="Rate-of-change catches drain failures before absolute lag thresholds trip.",
    ),
    StreamDetectorTemplate(
        template_id="throughput_producer_drop",
        title="Producer throughput drop",
        category="throughput",
        description="Detect an unexpected drop in topic producer throughput.",
        resource_type="topic",
        metric="producer_throughput",
        method="ewma_deviation",
        direction="low",
        baseline_window_seconds=86_400,
        evaluation_window_seconds=1_800,
        evaluation_interval_seconds=300,
        seasonal_mode="hour_of_day",
        rationale="Seasonal EWMA separates an off-peak lull from a genuine upstream stall.",
    ),
    StreamDetectorTemplate(
        template_id="throughput_pathway",
        title="Pathway throughput anomaly",
        category="throughput",
        description="Detect abnormal end-to-end pathway throughput in either direction.",
        resource_type="pathway",
        metric="throughput",
        method="robust_zscore",
        direction="both",
        baseline_window_seconds=86_400,
        evaluation_window_seconds=1_800,
        evaluation_interval_seconds=300,
        rationale="Both-direction detection surfaces stalls and runaway replays alike.",
    ),
)

_BY_ID: dict[str, StreamDetectorTemplate] = {template.template_id: template for template in STREAM_DETECTOR_TEMPLATES}


def list_templates(category: str | None = None) -> list[StreamDetectorTemplate]:
    """Return templates, optionally filtered by authoring category."""
    if category is None:
        return list(STREAM_DETECTOR_TEMPLATES)
    return [template for template in STREAM_DETECTOR_TEMPLATES if template.category == category]


def get_template(template_id: str) -> StreamDetectorTemplate | None:
    return _BY_ID.get(template_id)
