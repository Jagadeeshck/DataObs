# Administration Console threat model

Assets are access grants, tenant isolation, administrator continuity, identity privacy, and audit integrity. Threats include DOM/URL disclosure, stale cross-tenant data, role/scope injection, privilege escalation, OCC overwrite, duplicate destructive mutation, misleading optimistic state, and telemetry leakage. Controls are server authority, permission gates as navigation UX only, trusted membership selectors, encoded opaque paths, request abortion, canonical options, review/confirmation, If-Match, unique operation keys, safe error categories, no destructive retry, and backend last-administrator enforcement.

Residual gaps are the unbounded list API, missing audit/effective-access/catalogue APIs, incomplete ETag headers, and unavailable hosted evidence. These are shown honestly and require Team 0 contracts rather than browser workarounds.
