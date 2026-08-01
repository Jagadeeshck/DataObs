LIMITATIONS = (
    "Account Usage evidence may arrive after the underlying event",
    "Query text is intentionally excluded",
    "last_altered is metadata-change evidence, not guaranteed business-data freshness",
    "No row-level profiling or canonical lineage is produced",
    "Enterprise-only evidence is outside v1",
    "Output is not proof of complete Snowflake account coverage",
)

CHECKPOINT_FAMILIES = ("query_history", "warehouse_load", "warehouse_metering", "table_storage", "catalog_inventory")
