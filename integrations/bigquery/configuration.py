from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .authentication import Authentication, parse_authentication
from .errors import safe_error
from .identifiers import dataset_id, location_id, project_id


@dataclass(frozen=True)
class Project:
    project_id: str
    locations: tuple[str, ...]
    include_datasets: tuple[str, ...]
    exclude_datasets: tuple[str, ...]


@dataclass(frozen=True)
class BigQueryConfiguration:
    authentication: Authentication
    projects: tuple[Project, ...]
    metadata: Mapping[str, Any]
    jobs: Mapping[str, Any]
    storage: Mapping[str, Any]
    reservations: Mapping[str, Any]
    query_execution: Mapping[str, Any]
    limits: Mapping[str, int]
    allow_legacy_service_account_key: bool


def keys(x, allowed):
    if not isinstance(x, Mapping) or set(x) - set(allowed):
        raise safe_error("invalid_configuration")


def integer(x, n, d, lo, hi):
    v = x.get(n, d)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise safe_error("invalid_configuration")
    return v


def parse_configuration(raw: Mapping[str, Any]) -> BigQueryConfiguration:
    keys(
        raw,
        {
            "authentication",
            "projects",
            "metadata",
            "jobs",
            "storage",
            "reservations",
            "query_execution",
            "limits",
            "allow_legacy_service_account_key",
        },
    )
    legacy = raw.get("allow_legacy_service_account_key", False)
    if not isinstance(legacy, bool):
        raise safe_error("invalid_configuration")
    auth = parse_authentication(raw.get("authentication", {"type": "application_default"}), allow_legacy=legacy)
    ps = raw.get("projects")
    if not isinstance(ps, list) or not ps:
        raise safe_error("invalid_configuration")
    projects = []
    for p in ps:
        keys(p, {"project_id", "locations", "include_datasets", "exclude_datasets"})
        loc = p.get("locations")
        if not isinstance(loc, list) or not loc:
            raise safe_error("invalid_configuration")
        inc = tuple(dataset_id(x) for x in p.get("include_datasets", ()))
        exc = tuple(dataset_id(x) for x in p.get("exclude_datasets", ()))
        if set(inc) & set(exc):
            raise safe_error("invalid_configuration")
        locations = tuple(location_id(x) for x in loc)
        if len(set(locations)) != len(locations):
            raise safe_error("invalid_configuration")
        projects.append(Project(project_id(p.get("project_id")), locations, inc, exc))
    if len({p.project_id for p in projects}) != len(projects):
        raise safe_error("invalid_configuration")
    meta = raw.get("metadata", {})
    jobs = raw.get("jobs", {})
    storage = raw.get("storage", {})
    reservations = raw.get("reservations", {})
    query = raw.get("query_execution", {})
    limits = raw.get("limits", {})
    keys(
        meta,
        {
            "include_tables",
            "include_views",
            "include_materialized_views",
            "include_external_tables",
            "include_columns",
            "include_models",
            "include_routines",
            "include_labels",
        },
    )
    keys(
        jobs,
        {
            "enabled",
            "mode",
            "lookback_seconds",
            "overlap_seconds",
            "maximum_rows_per_location",
            "include_timeline_aggregation",
            "timeline_bucket_seconds",
        },
    )
    keys(storage, {"enabled", "maximum_rows_per_location"})
    keys(reservations, {"enabled", "administration_project", "locations", "include_utilisation"})
    keys(query, {"billing_project", "maximum_bytes_billed", "timeout_seconds", "page_size"})
    keys(
        limits,
        {
            "maximum_projects",
            "maximum_locations_per_project",
            "maximum_datasets_per_project",
            "maximum_tables_per_dataset",
            "maximum_columns",
            "maximum_models",
            "maximum_routines",
            "maximum_pages",
            "maximum_observations",
            "maximum_concurrent_requests",
        },
    )
    maxp = integer(limits, "maximum_projects", 20, 1, 20)
    if len(projects) > maxp or any(
        len(p.locations) > integer(limits, "maximum_locations_per_project", 20, 1, 20) for p in projects
    ):
        raise safe_error("invalid_configuration")
    look = integer(jobs, "lookback_seconds", 3600, 60, 86400 * 30)
    overlap = integer(jobs, "overlap_seconds", 900, 0, look)
    if overlap > look:
        raise safe_error("invalid_configuration")
    if query.get("billing_project") is not None:
        project_id(query["billing_project"])
    if reservations.get("administration_project") is not None:
        project_id(reservations["administration_project"])
    if reservations.get("locations") is not None:
        tuple(location_id(x) for x in reservations["locations"])
    bounds = {
        "maximum_projects": maxp,
        "maximum_locations_per_project": integer(limits, "maximum_locations_per_project", 20, 1, 20),
        "maximum_datasets_per_project": integer(limits, "maximum_datasets_per_project", 5000, 1, 5000),
        "maximum_tables_per_dataset": integer(limits, "maximum_tables_per_dataset", 50000, 1, 50000),
        "maximum_columns": integer(limits, "maximum_columns", 500000, 1, 500000),
        "maximum_models": integer(limits, "maximum_models", 10000, 1, 10000),
        "maximum_routines": integer(limits, "maximum_routines", 10000, 1, 10000),
        "maximum_pages": integer(limits, "maximum_pages", 1000, 1, 1000),
        "maximum_observations": integer(limits, "maximum_observations", 500000, 1, 500000),
        "maximum_concurrent_requests": integer(limits, "maximum_concurrent_requests", 8, 1, 32),
    }
    return BigQueryConfiguration(auth, tuple(projects), meta, jobs, storage, reservations, query, bounds, legacy)
