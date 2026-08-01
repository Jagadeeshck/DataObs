# Certification evidence contract

Evidence must include `repository`, `commit_sha`, `base_sha`, `workflow`, `workflow_run_id`, `job`, `event`, `branch`, `generated_at`, `tool_versions`, `Elasticsearch_version`, `terminal_migration`, `test_summaries`, `artifact_inventory`, `security_scan_summary`, `tenant_isolation_result`, `migration_immutability_result`, and `independent_verification_result`.

Promotion states are `planned`, `implemented`, `functional_unvalidated`, `certified`, and `release_blocked`. Local-only execution cannot promote a capability to `certified`. Producers must use the existing provenance and independent verifier established by PR #179 (`scripts/certification/provenance.py` and `verify_artifacts.py`); no alternate envelope or verifier is permitted.
