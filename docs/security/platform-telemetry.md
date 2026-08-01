# Platform telemetry security

Telemetry is opt-in, uses secret/environment credential injection, verifies transport by default in production configuration, strips endpoint query strings, and fails open. Metric labels exclude identities, tenant/environment selectors, IDs, paths, bodies, claims, queries and exception messages. Request IDs are trace/log correlation only. `/metrics` must remain cluster-internal behind NetworkPolicy. Browser telemetry remains Team 5-owned.
