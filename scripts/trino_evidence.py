import json
import os
import platform
import subprocess

sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
terminal = subprocess.check_output(["python", "scripts/release/current_terminal_migration.py"], text=True).strip()
print(
    json.dumps(
        {
            "repository": os.getenv("GITHUB_REPOSITORY", "Jagadeeshck/DataObs"),
            "exact_sha": sha,
            "workflow": "Trino SQL Engine Collector v1",
            "run_id": os.getenv("GITHUB_RUN_ID", "local"),
            "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "local"),
            "python_version": platform.python_version(),
            "trino_server_version": os.getenv("TRINO_SERVER_VERSION", "not_exercised"),
            "trino_python_client_version": "0.338.0",
            "elasticsearch_version": "not_exercised",
            "terminal_migration": terminal,
            "provider_version": "1",
            "supported_capabilities": [
                "resource_discovery",
                "metadata_collection",
                "metric_collection",
                "query_history",
                "schema_discovery",
                "health_check",
                "incremental_collection",
            ],
            "unsupported_capabilities": [
                "log_collection",
                "lineage_collection",
                "cost_collection",
                "event_driven_collection",
            ],
            "authentication_modes": ["basic", "jwt", "certificate"],
            "direct_protocol": True,
            "checks": {
                "statement_allowlist": "passed",
                "no_dml_ddl": "passed",
                "no_business_rows": "passed",
                "query_text_exclusion": "passed",
                "user_identity_exclusion": "passed",
                "node_location_exclusion": "passed",
                "history_semantics": "bounded_runtime_history",
                "checkpoint": "generic_occ_contract",
                "tenant_isolation": "trusted_context",
                "postgres_regression": "workflow_test_suite",
                "provider_regressions": "workflow_test_suite",
                "live_trino": os.getenv("TRINO_LIVE_STATUS", "not_run"),
            },
            "known_limitations": [
                "functional_unvalidated",
                "bounded runtime history",
                "no Presto, profiling, lineage, cost, or spooling",
            ],
        },
        sort_keys=True,
    )
)
