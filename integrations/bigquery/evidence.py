LIMITATIONS = (
    "Only explicitly configured projects are observed",
    "Visibility reflects the collector principal's IAM permissions; organisation-wide or complete coverage is not claimed",
    "Jobs are provider-native source evidence, not canonical DataObs runs",
    "Query text and user identities are intentionally excluded",
    "INFORMATION_SCHEMA queries are location-specific",
    "Table-storage evidence may be delayed",
    "Table metadata timestamps do not prove business-data freshness",
    "Operational consumption is not monetary cost",
    "No table rows or column values are read",
    "No production-readiness or certification claim exists without exact-commit hosted evidence",
)
CHECKPOINT_FAMILIES = (
    "datasets",
    "tables",
    "models",
    "routines",
    "jobs",
    "job_timeline",
    "storage",
    "reservations",
    "reservation_utilisation",
)
