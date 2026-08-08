from .sql import REGISTRY, catalog_registry


class PrestoDialect:
    engine_type = "presto"
    direct_protocol = True
    supports_spooling = False
    materialized_view_inventory = "unsupported"

    def metadata_statement(self, family, *, catalog=None):
        return (catalog_registry(catalog) if catalog else REGISTRY).get(family)
