from ..sql import REGISTRY
from .common import execute


def collect(connection, context, cfg, cluster):
    yield from execute(connection, REGISTRY, "materialized_views", context, cfg, cluster)
