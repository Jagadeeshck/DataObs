from ..sql import catalog_registry
from .common import execute


def collect(connection, context, cfg, cluster, catalog):
    for item in execute(connection, catalog_registry(catalog), "schemas", context, cfg, cluster):
        name = item.source_evidence["schema_name"]
        if (
            name != "information_schema"
            and (not cfg.schema_include or name in cfg.schema_include)
            and name not in cfg.schema_exclude
        ):
            yield item
