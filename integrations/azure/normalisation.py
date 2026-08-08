from datetime import datetime, timezone
from typing import Mapping

from packages.collectors.sdk import ResourceObservation


def value(x, n, d=None):
    return x.get(n, d) if isinstance(x, Mapping) else getattr(x, n, d)


def safe(x, fields):
    return {n: value(x, n) for n in fields if value(x, n) is not None}


def observation(context, cfg, region, service, kind, native, name, evidence):
    return ResourceObservation(
        "azure",
        cfg.subscription_id,
        region or "global",
        service,
        kind,
        native,
        name,
        datetime.now(timezone.utc),
        context.collection_run_id,
        source_evidence={"evidence_family": kind, **evidence},
    )


def resource_id(cfg, rg, provider, kind, name):
    return f"/subscriptions/{cfg.subscription_id}/resourceGroups/{rg}/providers/{provider}/{kind}/{name}".lower()


def duration_ms(start, end):
    return int((end - start).total_seconds() * 1000) if start and end else None
