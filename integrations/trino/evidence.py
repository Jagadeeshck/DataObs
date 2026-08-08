import hashlib

HISTORY_COMPLETENESS = "bounded_runtime_history"
CHECKPOINT_FAMILIES = (
    "catalogs",
    "schemas",
    "relations",
    "columns",
    "materialized_views",
    "runtime_queries",
    "runtime_tasks",
    "cluster_health",
)
LIMITATIONS = (
    "Runtime query evidence is bounded coordinator memory, not complete history",
    "SQL text and user identity are excluded at source",
    "No profiling, row sampling, lineage, costs, or custom SQL",
    "Direct protocol only; spooling is not certified",
)


def cluster_id(host: str, port: int) -> str:
    return "trino:" + hashlib.sha256(f"{host.lower()}:{port}".encode()).hexdigest()
