from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .authentication import Authentication, parse_authentication
from .errors import error

PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")


@dataclass(frozen=True)
class ProjectConfiguration:
    project_id: str
    include_topics: tuple[str, ...]
    exclude_topics: tuple[str, ...]
    include_subscriptions: tuple[str, ...]
    exclude_subscriptions: tuple[str, ...]


@dataclass(frozen=True)
class GoogleCloudConfiguration:
    services: frozenset[str]
    authentication: Authentication
    projects: tuple[ProjectConfiguration, ...]
    pubsub: Mapping[str, bool]
    monitoring: Mapping[str, int]
    limits: Mapping[str, int]


def _closed(raw: object, allowed: set[str], family: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) - allowed:
        raise error("invalid_configuration", family)
    return raw


def _bounded(raw: Mapping[str, Any], key: str, default: int, maximum: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise error("invalid_configuration", "limits")
    return value


def parse_gcp_configuration(raw: Mapping[str, Any]) -> GoogleCloudConfiguration:
    raw = _closed(
        raw,
        {
            "services",
            "authentication",
            "projects",
            "pubsub",
            "monitoring",
            "limits",
            "allow_legacy_service_account_key",
        },
        "configuration",
    )
    services = raw.get("services")
    if not isinstance(services, (list, tuple)) or set(services) != {"pubsub"}:
        raise error("invalid_configuration", "services")
    allow_legacy = raw.get("allow_legacy_service_account_key", False)
    if not isinstance(allow_legacy, bool):
        raise error("invalid_configuration", "authentication")
    projects_raw = raw.get("projects")
    if not isinstance(projects_raw, (list, tuple)) or not projects_raw:
        raise error("invalid_configuration", "projects")
    if len(projects_raw) > 20:
        raise error("invalid_configuration", "projects")
    projects = []
    project_keys = {"project_id", "include_topics", "exclude_topics", "include_subscriptions", "exclude_subscriptions"}
    for item in projects_raw:
        item = _closed(item, project_keys, "projects")
        project_id = item.get("project_id")
        if not isinstance(project_id, str) or not PROJECT.fullmatch(project_id):
            raise error("invalid_configuration", "projects")
        selections = []
        for key in ("include_topics", "exclude_topics", "include_subscriptions", "exclude_subscriptions"):
            value = item.get(key, ())
            if not isinstance(value, (list, tuple)) or any(not isinstance(entry, str) or not entry for entry in value):
                raise error("invalid_configuration", "projects")
            selections.append(tuple(value))
        projects.append(ProjectConfiguration(project_id, *selections))
    flags = {
        "include_topics",
        "include_subscriptions",
        "include_dead_letter_relationships",
        "include_topic_retention",
        "include_subscription_retention",
        "include_delivery_configuration",
        "include_metrics",
    }
    pubsub_raw = _closed(raw.get("pubsub", {}), flags, "pubsub")
    pubsub = {key: pubsub_raw.get(key, True) for key in flags}
    if any(not isinstance(value, bool) for value in pubsub.values()):
        raise error("invalid_configuration", "pubsub")
    monitoring_raw = _closed(raw.get("monitoring", {}), {"lookback_seconds", "alignment_period_seconds"}, "monitoring")
    monitoring = {
        "lookback_seconds": _bounded(monitoring_raw, "lookback_seconds", 900, 86400),
        "alignment_period_seconds": _bounded(monitoring_raw, "alignment_period_seconds", 60, 3600),
    }
    limits_raw = _closed(
        raw.get("limits", {}),
        {
            "maximum_projects",
            "maximum_topics_per_project",
            "maximum_subscriptions_per_project",
            "maximum_pages",
            "maximum_metric_series",
            "maximum_metric_points",
            "maximum_observations",
            "request_timeout_seconds",
            "total_timeout_seconds",
        },
        "limits",
    )
    specs = {
        "maximum_projects": (20, 100),
        "maximum_topics_per_project": (10000, 100000),
        "maximum_subscriptions_per_project": (50000, 200000),
        "maximum_pages": (1000, 10000),
        "maximum_metric_series": (100000, 500000),
        "maximum_metric_points": (500000, 1000000),
        "maximum_observations": (500000, 1000000),
        "request_timeout_seconds": (15, 120),
        "total_timeout_seconds": (300, 3600),
    }
    limits = {key: _bounded(limits_raw, key, default, maximum) for key, (default, maximum) in specs.items()}
    if len(projects) > limits["maximum_projects"]:
        raise error("invalid_configuration", "projects")
    return GoogleCloudConfiguration(
        frozenset(services),
        parse_authentication(raw.get("authentication"), allow_legacy=allow_legacy),
        tuple(projects),
        pubsub,
        monitoring,
        limits,
    )
