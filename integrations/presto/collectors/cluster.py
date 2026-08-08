from ..sql import REGISTRY
from .common import execute


def collect(connection, context, cfg, cluster):
    yield from execute(connection, REGISTRY, "cluster", context, cfg, cluster)
