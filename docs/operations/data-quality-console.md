# Operating the Data Quality Console

Serve the API with a tenant-scoped monitor repository and optional runtime-health object, then build the Console normally. `/api/v1/quality/overview` deliberately returns partial evidence when finding, coverage, observation or runtime sources are missing. A disconnected runtime returns typed HTTP 503 and must be investigated rather than interpreted as zero workers or zero backlog.

The Console defaults to manual refresh. Operators should verify tenant and environment selectors before interpreting evidence. Warnings, missing inputs, source coverage and request IDs support investigation. A stale monitor indicates collection recency risk, not necessarily a failed check. Recommendation rows are proposals only.

Certification requires the feature workflow to execute backend isolation/permission tests, Console typecheck/test/build, Chromium Playwright and axe against Elasticsearch 9.4.2 and PostgreSQL, retain exact-commit `data-quality-console-v1-evidence`, and independently verify it. Until that succeeds the capability is functional but unvalidated.
