# Tenant and environment isolation certification

The deterministic matrix is tenant A/B crossed with production/test. Adversarial tests deny cross-tenant reads/mutations, cross-environment access, Console/API permission bypass, unknown routes, principal header override, query-filter bypass, mixed bulk writes and interactive privileges for service identities. Restore and audit checks preserve tenant/environment attribution; platform-admin actions are explicitly audited.

`tenant-isolation-report.json`, redacted JUnit and `security-redaction-report.json` must be exact-SHA artifacts. Skipped cases remain pending. The hosted secured-stack matrix has not run for this change, so certification is **pending**.
