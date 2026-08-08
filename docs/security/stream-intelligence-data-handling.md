# Stream Intelligence data handling

All queries require authenticated tenant and environment context and an allowlisted resource binding. APIs never accept Elasticsearch DSL or field names. Pagination cursors cryptographically bind scope, route, filters, sorting, page size and search-after state and expire.

The runtime processes operational metrics and metadata only. It never reads or persists Kafka message payloads, credentials, or secrets. Failure findings are candidates; a safe fingerprint may be stored, but message content is prohibited. Missing, partial, stale, estimated and inferred observations remain distinguishable. Forecasts communicate uncertainty and never assert future loss as certain.

Mutations require an authenticated actor, idempotency fingerprint where created, ETag/If-Match thereafter, Elasticsearch OCC, and a current fencing token for runtime writes. Tenant/environment form part of every deterministic SHA-256 identity, preventing cross-scope collision. Team 3 indices and private repositories are not accessed.
