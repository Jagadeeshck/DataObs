from ..sql import catalog_registry
from .common import execute


def collect(connection, context, cfg, cluster, catalog):
    yield from execute(connection, catalog_registry(catalog), "relations", context, cfg, cluster)
