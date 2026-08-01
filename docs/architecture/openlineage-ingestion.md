# OpenLineage ingestion

`POST /api/v1/openlineage/events` is the canonical collector endpoint; the two older lineage endpoints are compatibility aliases. The authenticated tenant and environment are injected by the server and form part of every job and run identity.

The boundary accepts START, RUNNING, COMPLETE, FAIL, ABORT, and OTHER run events. It enforces bounded JSON shape, timestamp and identity fields, dataset arrays, strings, nesting, and unknown facets. Secret-like keys, SQL, queries, environments, and stack traces are recursively redacted. Only normalized evidence, safe facets, and a bounded redacted unknown-facet section are persisted.

Event identity is deterministic. An exact retry is a no-op; reusing an explicit event identity with different content is a conflict. Evidence is append-only while current projections use terminal-aware lifecycle precedence, so late non-terminal events cannot reopen terminal runs.
