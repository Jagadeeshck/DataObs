# Snowflake warehouse collector v1

The explicitly registered `snowflake` generation `1` provider runs per tenant/environment/integration through the
Integration SDK and Collection Manager. A per-execution connection uses UTC, bounded timeouts and a non-sensitive query
tag. The optional official connector is lazy imported. Fixed, explicit-column templates bind all values, use bounded
iteration, deterministic ordering and limits. Configuration cannot supply SQL, hosts, session parameters or identifiers
outside the strict grammar.

Families are account identity, warehouse/resource-monitor inventory, catalog and columns, query history, warehouse
load, metering consumption, table storage, metadata freshness and explainable partial evidence. Query history never
selects SQL text, identity/surveillance/client fields or raw errors. Deterministic IDs include a hashed account scope.
Measured zero is distinct from missing metrics. Metering is operational credits—not cost/FinOps. `last_altered` uses
`freshness_method=metadata_last_altered` and is not business-data freshness.

Account Usage is delayed and output cannot prove complete coverage. Separate logical checkpoint families are query,
load, metering, storage and catalog; the generic runtime persists evidence before OCC advancement. Access History is
deferred: it is Enterprise-only, its structured payload changed in 2026, and any parser/projection requires Team 2
review. No lineage, profiling, mutation, login/session surveillance, incident or remediation capability exists.
