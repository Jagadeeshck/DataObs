# Platform supportability Console data handling

Routes and Quick Find entries require `platform_operations:read`; the backend permission remains authoritative. Requests use authenticated transport and do not bypass server scoping.

Approved telemetry is low-cardinality state/category/bucket metadata. Request IDs, fingerprints, bundle IDs, SHAs, issue text, diagnostic text and infrastructure/tenant/environment identifiers are prohibited. A defense-in-depth key classifier rejects secret, token, password, credential, private-key, authorization and cookie classes, but frontend filtering is not a security boundary.

Only typed fields render. Raw configuration, raw response JSON, workflow environments, headers, claims, logs and unredacted support bundles are excluded.
