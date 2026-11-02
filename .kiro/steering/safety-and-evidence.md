---
inclusion: always
---
# Non-negotiable safety, reliability and release integrity

1. Do not weaken auth, RBAC, tenant/environment isolation, mapping strictness, evidence validation, source SHA verification, or mandatory CI.
2. Do not manually mark release `GO`, security `PASS`, a platform `supported`, or data `healthy` based on source changes or local tests.
3. Respect distinct states: measured zero / missing / stale / unavailable / partial / unknown / error.
4. Never edit previously released migrations; additive changes require versioned forward migration and tests.
5. Do not enable autonomous remediation or unapproved external side effects. Mock real pager/ticket/notification sends in tests.
6. No secrets, credentials or personal/sensitive payloads in repo, prompts, logs, tests or artifacts.
7. Don't disable tests or hide failed/suspended integration tests to make a release green.
8. Don't claim supported cloud/database connectors if Collection Manager is un-packaged or real runtime evidence missing.
9. Stop release promotion when mandatory Gate 0, security, destructive recovery, clean install, cross-tenant, browser/accessibility, SBOM/signature/provenance or independent verification is failing.
10. Version transition to v1.0.0 / Elastic 9.5.5 requires a consistent compatibility matrix, migrations, deployment and explicit authority; historical v0.2.0 results do not certify v1.0.0.
