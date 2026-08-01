# Console self-observability architecture

The fail-open path is `Browser → same-origin OTLP/HTTP gateway → existing OpenTelemetry Collector → Elasticsearch`. The browser has no Elasticsearch or collector credentials and supplies no authoritative user or tenant identity. Telemetry defaults off; malformed configuration disables export while retaining safe in-memory diagnostics.

`observability/bootstrap.ts` initializes once, registers document-load and allowlisted fetch instrumentation, installs parent-based ratio sampling and bounded batching, and starts a startup span without awaiting network I/O. `navigation.tsx` maps locations through the authoritative route manifest. `requests.ts` wraps the shared transport with safe templates. `webVitals.ts` records LCP, INP, CLS, FCP, TTFB, and bounded long-task totals. Errors are deduplicated and rate-limited before export.

The package deliberately excludes session replay, DOM/form/console capture, user analytics, IdP instrumentation, request/response bodies, and browser-side persistence. Unsupported browser observers and exporter failures are ignored by product execution and exposed only as safe diagnostics.
