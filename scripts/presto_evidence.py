import importlib.metadata
import json
import os
import platform
import subprocess

sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print(
    json.dumps(
        {
            "repository": "Jagadeeshck/DataObs",
            "exact_sha": sha,
            "workflow_run_id": os.getenv("GITHUB_RUN_ID", "local"),
            "python_version": platform.python_version(),
            "presto_server_version": "0.298.1 (target; live not run)",
            "presto_python_client_version": importlib.metadata.version("presto-python-client"),
            "sql_engine_foundation_commit": sha,
            "provider_version": "1",
            "elasticsearch_version": "not exercised",
            "terminal_migration": "0028_pathway_investigation_history",
            "capabilities": [
                "resource_discovery",
                "metadata_collection",
                "metric_collection",
                "query_history",
                "schema_discovery",
                "health_check",
                "incremental_collection",
            ],
            "authentication_mode": "basic",
            "client_compatibility": "expected; import/auth gate passed, live lifecycle pending",
            "sql_safety": "passed",
            "mutation_prohibition": "passed",
            "business_row_prohibition": "passed",
            "query_text_exclusion": "passed",
            "user_exclusion": "passed",
            "node_location_exclusion": "passed",
            "next_uri_safety": "passed",
            "history_completeness": "bounded_runtime_history",
            "history_gap_test": "passed",
            "checkpoint_result": "persist observations and run before OCC advance",
            "trino_regression": "workflow target",
            "provider_regressions": "workflow target",
            "postgresql_scanner_regression": "workflow target",
            "live_test_status": "not_run",
            "status": "functional_unvalidated",
            "known_limitations": [
                "materialized views unsupported",
                "bounded runtime history only",
                "Basic authentication only",
                "hosted evidence pending",
            ],
        },
        sort_keys=True,
        indent=2,
    )
)
