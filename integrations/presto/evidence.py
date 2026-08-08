import hashlib

HISTORY_COMPLETENESS = "bounded_runtime_history"
CHECKPOINT_FAMILIES = (
    "cluster_health",
    "catalogs",
    "schemas",
    "relations",
    "columns",
    "runtime_queries",
    "runtime_tasks",
)
GAP_REASONS = (
    "coordinator_restart_possible",
    "runtime_history_evicted",
    "history_window_unavailable",
    "access_restricted",
    "server_identity_changed",
    "unknown_gap",
)
LIMITATIONS = (
    "Runtime evidence is bounded coordinator memory, not complete history",
    "SQL text and user identity are excluded at source",
    "Materialized-view inventory, profiling, lineage, costs, and custom SQL are unsupported",
    "REST query APIs are not used",
)


def cluster_id(host, port):
    return "presto:" + hashlib.sha256(f"{host.lower()}:{port}".encode()).hexdigest()
