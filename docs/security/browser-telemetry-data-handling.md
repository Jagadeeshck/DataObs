# Browser telemetry data handling

Browser telemetry is operational processing, not behavioral analytics. Data minimisation is enforced by a positive attribute allowlist, stable templates, redaction, bounded fingerprints, sampling, queues, and short-lived memory. Tenant/user IDs are not hashed: future correlation requires a backend-issued non-reversible bounded cohort reviewed separately.

CSP should retain `connect-src 'self'` for the preferred gateway. Any reviewed cross-origin gateway requires its exact HTTPS origin and narrow CORS; wildcard origins and credentials are forbidden. OTLP URLs cannot contain userinfo, query, or fragment and require HTTPS except localhost development. Trace headers propagate only to configured DataObs origins, never documentation or identity-provider traffic.

Public production source maps remain disabled. A future certification-only hidden-map artifact must be private, access-controlled, secret-scanned, retention-bounded, and never copied into served assets. Error telemetry remains useful through stable fingerprints without maps.
