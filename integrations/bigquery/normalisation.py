from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from packages.collectors.sdk import ResourceObservation


def value(x: object, n: str, d=None):
    return x.get(n, d) if isinstance(x, Mapping) else getattr(x, n, d)


def safe(raw: object, fields: tuple[str, ...]):
    return {n: value(raw, n) for n in fields if value(raw, n) is not None}


def observation(context, project, location, kind, native, name, evidence):
    return ResourceObservation(
        "bigquery",
        project,
        location,
        "bigquery",
        kind,
        native,
        name,
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence=evidence,
    )
