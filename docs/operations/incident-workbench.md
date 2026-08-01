# Operating the Incident Workbench

## Availability

Use the normal API health and migration readiness endpoints first. The workbench requires the Elasticsearch backend in production and reuses released incident, finding and collaboration resources. A missing provider configuration is intentionally shown as `not_configured`; lack of API support is `unsupported`; license denial and provider failure must remain `unlicensed` and `unavailable` respectively.

## Troubleshooting

* HTTP 400 cursor errors mean filters, environment, sorting or page size changed; restart pagination.
* HTTP 404 is scope-safe and can mean absent, different-tenant or different-environment data.
* HTTP 409 means the incident changed after it was read. Refresh, review the new revision and explicitly retry.
* HTTP 400 for a mutation without `Idempotency-Key` is intentional. Preserve one key for all retries of the same logical operation.
* `unknown` evidence means no safe measurement exists; it is not a measured zero.
* A `not_configured` preview is informational. Do not treat it as an execution attempt or success.

Audit logs and request IDs should be used for correlation without recording action payloads or evidence. Repository errors should be investigated without copying raw Elasticsearch source documents into tickets.

## Beta 1 limitations

Real Elasticsearch 9.4.2 was not available in the closure workspace, so strict-template execution remains to be certified by the opt-in environment; serializer tests use the generated production mapping. PITs live for two minutes and cursors for 15 minutes, so an expired PIT/cursor requires restarting the listing. A timeline failure after a mutation is recovered by retrying the identical idempotency key; a different payload with that key conflicts. A failure before the operation record is durable still requires operator investigation. Watchers, tasks, approvals and executions are displayed only when backed by their existing durable services; no external connector is fabricated.
