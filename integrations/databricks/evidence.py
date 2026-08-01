LIMITATIONS = (
    "Jobs and runs are provider-native source evidence; no canonical job, run, or task is created",
    "Query history is optional, privacy-restricted, and sourced from a Public Preview system table",
    "System-table evidence may be delayed or unavailable",
    "Only the configured workspace is observed",
    "Unity Catalog visibility reflects the collector principal's permissions",
    "No file contents, table data, SQL text, or user identity are read",
    "No production-readiness claim exists without exact-commit hosted proof",
)

CHECKPOINT_FAMILIES = ("unity_catalog", "sql_warehouses", "jobs", "job_runs", "query_history", "warehouse_events")
