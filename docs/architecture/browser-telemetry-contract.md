# Browser telemetry contract

All span attributes pass through `attributePolicy.ts`. Unknown attributes throw in development/tests and are dropped in production. Allowed values are service metadata, stable route/capability/team/navigation categories, bounded error fingerprints, validated request IDs, recovery/chunk categories, metric name/value/unit, method/status, and API route templates.

Never export identity, tenant/environment customer identifiers, dynamic entity IDs, query strings, headers, cookies, tokens, bodies, SQL/schema/connector content, free text, storage, or raw stacks. Route names come from manifest IDs. API paths replace UUIDs, numeric IDs, and long opaque segments with `:id`. Errors are length-bounded, redacted, fingerprinted, suppressed for 30 seconds, and capped at 20 per minute.

Trace sampling is parent-based and identity-independent. Critical errors are separately recorded within rate limits. Batch queues are runtime-bounded; overflow is discarded and counted. Page-hide flush is opportunistic and never blocks unload.
