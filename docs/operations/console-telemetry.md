# Operating Console telemetry

Set `console.observability.enabled=true` only after provisioning an approved same-origin OTLP/HTTP gateway. Configure service/version/environment, endpoint, trace ratio, capture switches, propagation allowlist, export interval, and queue limits through Helm runtime configuration. Never add endpoint credentials or query parameters.

The gateway must validate `Origin`, allow only Console origins and OTLP methods/headers, cap payload/body size, rate-limit, re-redact prohibited fields, discard unknown attributes, and set trustworthy deployment/tenancy fields server-side. The existing collector may then export to Elasticsearch; do not expose Elasticsearch to the browser. Current collector configuration is not automatically enabled for browser ingestion.

Rollback by setting `enabled=false`; no image rebuild is required. For 400/401/403, treat configuration or gateway policy as invalid. For 429/5xx/timeouts/offline states, verify collector health and rate limits; the application remains available and bounded batches are discarded rather than retried indefinitely.

Example ES|QL health query (field mappings may vary): `FROM traces-* | WHERE service.name == "dataobs-console" | STATS events=COUNT(*) BY service.version, dataobs.console.route_id`. Build views for route/API errors, latency, Web Vitals, chunk errors, long tasks, recovery actions, and releases without environment-specific saved-object IDs.
