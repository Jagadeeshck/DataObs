# Platform Console data handling

The feature displays metadata returned by Team 0 and never raw deployment configuration, credentials, tokens, API keys, passwords, private endpoints, kubeconfigs or secret variables. It does not persist fleet responses. Telemetry is allow-listed to low-cardinality page, resource-kind, state, outcome, duration/result buckets, drift and capacity categories; identifiers, labels, payloads, free text and actors are dropped.

Direct routes require `platform_operations:read`. Ordinary tenant users therefore cannot render the component, and API authorization remains the final cross-tenant boundary. Fleet requests do not inherit a tenant-scoped product context. No lifecycle mutation registry entries exist in v1.
