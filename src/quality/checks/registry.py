"""Quality check registry and factory helpers.

This module is the single place where built-in check type strings are mapped to
implementations. Keeping registration centralized makes feature work predictable:
new checks only need to be imported and registered here, while the scheduler,
API, tests, and documentation can rely on the same names.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from elasticsearch import Elasticsearch

from .base import BaseCheck
from .distribution_drift_check import DistributionDriftCheck
from .null_check import NullCheck
from .referential_integrity_check import ReferentialIntegrityCheck
from .row_count_check import RowCountCheck
from .schema_check import SchemaCheck
from .uniqueness_check import UniquenessCheck
from .value_range_check import ValueRangeCheck

CHECK_REGISTRY: Dict[str, Type[BaseCheck]] = {
    "distribution_drift": DistributionDriftCheck,
    "null_check": NullCheck,
    "referential_integrity": ReferentialIntegrityCheck,
    "row_count": RowCountCheck,
    "schema_change": SchemaCheck,
    "uniqueness": UniquenessCheck,
    "value_range": ValueRangeCheck,
}


def supported_check_types() -> tuple[str, ...]:
    """Return supported check type names in stable display order."""

    return tuple(sorted(CHECK_REGISTRY))


def build_check(
    check_type: str,
    *,
    es_client: Elasticsearch | None = None,
    config: Mapping[str, Any] | None = None,
) -> BaseCheck:
    """Create a check implementation for *check_type*.

    ``schema_change`` and row-count anomaly detection need Elasticsearch access.
    Distribution drift is configured around a specific table/column, so the
    factory reads those values from ``config`` when that type is requested.
    """

    try:
        check_class = CHECK_REGISTRY[check_type]
    except KeyError as exc:
        supported = ", ".join(supported_check_types())
        raise ValueError(f"Unsupported check type {check_type!r}. Supported types: {supported}") from exc

    if check_type == "schema_change":
        if es_client is None:
            raise ValueError("schema_change checks require an Elasticsearch client")
        return SchemaCheck(es_client)
    if check_type == "row_count":
        return RowCountCheck(es_client)
    if check_type == "distribution_drift":
        cfg = dict(config or {})
        return DistributionDriftCheck(
            table=cfg.get("table") or cfg.get("dataset", ""),
            column=cfg.get("column", ""),
            z_score_threshold=cfg.get("z_score_threshold", 3.0),
            baseline_store=cfg.get("baseline_store"),
            null_rate_threshold=cfg.get("null_rate_threshold", 0.1),
        )
    return check_class()
