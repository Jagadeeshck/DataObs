# Lineage impact data handling

Tenant and environment derive from authenticated request context and are predicates in every repository query. Identifiers and graph bounds are validated; APIs accept neither Elasticsearch DSL nor graph query languages. Evidence references are bounded metadata—not raw OpenLineage payloads, SQL, rows, stack traces, or secrets. Cross-tenant lookups return no document. Persisted analysis requires an idempotency key and the method-aware lineage analysis permission.
