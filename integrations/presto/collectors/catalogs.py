from ..sql import REGISTRY
from .common import execute


def collect(connection, context, cfg, cluster):
    for item in execute(connection, REGISTRY, "catalogs", context, cfg, cluster):
        name = item.source_evidence["catalog_name"]
        if (not cfg.catalog_include or name in cfg.catalog_include) and name not in cfg.catalog_exclude:
            yield item
