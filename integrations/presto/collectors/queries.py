from datetime import datetime, timedelta, timezone

from ..sql import REGISTRY
from .common import execute


def collect(connection, context, cfg, cluster):
    start = datetime.now(timezone.utc) - timedelta(seconds=cfg.runtime["queries"]["lookback_seconds"])
    yield from execute(
        connection, REGISTRY, "queries", context, cfg, cluster, (start, cfg.runtime["queries"]["maximum_queries"])
    )
