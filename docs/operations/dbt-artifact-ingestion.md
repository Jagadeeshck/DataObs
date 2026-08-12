# dbt artifact ingestion

Submit a typed request to `POST /api/v1/dbt/artifacts`; tenant and environment come only from authenticated request context. Required inputs are project ID/name, artifact type and JSON artifact. Upload manifest, run-results, catalog and sources/freshness independently.

The service validates size, safe fields, schema URI and dbt version; fingerprints canonical JSON; appends a create-only event; and updates bounded projections. Exact replays return `replayed`. Errors use safe codes including `unsupported_schema_version`, `artifact_too_large`, `resource_limit_exceeded`, `unsafe_field_detected`, and `invalid_artifact` without echoing rejected content.

Never provide `profiles.yml`, compiled/raw SQL, hooks, secrets, fixture rows, failing rows, or environment dictionaries. The runtime does not execute dbt or access warehouses.
