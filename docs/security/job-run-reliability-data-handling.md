# Job/run reliability data handling

Tenant and environment come from trusted request context and are predicates inside repository operations. Cross-scope absence is returned as not found. Cursors are signed, expiring and bound to endpoint, scope, filters and sort. Mutations require actor attribution and ETag matching. Evidence references must be bounded and failure summaries redacted; raw SQL, rows, event payloads, secrets and stack traces are prohibited.
