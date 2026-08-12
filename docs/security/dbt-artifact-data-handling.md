# dbt artifact data handling

Artifacts are untrusted. The parser rejects restricted code, SQL, hooks, environment, credential, token, password, key, profile, fixture-row and raw-row fields before normalization. Descriptions, identifiers, dependencies, tags, depth, resources and columns are bounded. Adapter response persistence uses only allowlisted numeric row counts and bounded codes; `run_results.message` is never retained.

Tenant/environment are trusted server context, every repository read is tenant/environment scoped, and deterministic IDs include both. Telemetry must use bounded artifact/status dimensions and never model, test, column or metric names. Raw manifests are not a long-term projection.
