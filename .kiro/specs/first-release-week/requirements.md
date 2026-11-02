# Requirements — DataObs v1.0.0 first supported release (week ending 2026-11-06)

## Purpose

Deliver the smallest evidence-backed, supportable DataObs distribution while establishing
the Elastic Enterprise foundation for post-release capability layers. Current v1.0.0 /
ES 9.5.5 source declaration is not itself a successful release.

## Platform and license

DataObs v1.0.0 targets **Elasticsearch 9.5.5 Enterprise** license. All `xpack.*`
features (ML, Watcher, FLS, CCS, Transform, ESRE, Fleet) are available in the target
environment. Local development uses the 30-day trial license.

## Functional requirements

- **R1**: Secure, tenant-scoped API and Console can be installed, started, and used via
  one documented supported deployment profile (Helm on Kubernetes with external ES, and
  Docker Compose MVP for local).
- **R2**: End-to-end observed signal journey: quality check → OTel → Collector → ES →
  finding → deduplicated incident → authorized retrieval.
- **R3**: Streams/Pathways, Jobs/Run, Data Products included only within the certified
  matrix — not claimed beyond hosted-evidence scope.
- **R4**: Missing/unknown/stale/partial/zero evidence accurately reported and traceable.
- **R5**: Provider support statements match actual packaged and certified runtimes only.
- **R6**: Production safety: OIDC/JWKS/RBAC, tenant/environment isolation enforced at
  API and Elasticsearch layers, least privilege, approval-bound notifications.

## Non-functional requirements

- **R7**: Exact-SHA complete CI: shared checks, real ES 9.5.5 migration (first and
  repeat), Kubernetes/Helm smoke, Compose MVP clean start, destructive backup/restore,
  browser/a11y, security, SBOM/signatures/provenance.
- **R8**: One consistent version matrix: DataObs 1.0.0, ES/Kibana 9.5.5,
  elasticsearch[async]==9.5.0, Helm chart 1.0.0.
- **R9**: Independently verified artifact digest/run/SHA, supported platform, security
  PASS, and protected authority GO before publication.
- **R10**: No competitor product names in any public-facing file (code, docs, comments,
  tests, configs). Internal references live in `.kiro/strategy/` only.
- **R11**: Elastic Enterprise features (ML, Watcher, etc.) documented in
  `.kiro/strategy/elastic-enterprise-features.md` before implementation.

## Acceptance criteria

Given a clean supported environment, when operator follows `RELEASE.md` install docs:
- API and Console start cleanly, migrations apply safely on repeat runs
- Authenticated tenant flows work (OIDC → RBAC → scoped data)
- E2E quality signal path produces a findable incident
- Destructive restore recovers to identical state
- Browser/a11y suites pass (zero serious/critical axe violations)
- Release authority returns GO with verified artifacts

**Any acceptance failure = NO_GO.**
