# Beta 1 integrated certification preflight audit

## Decision

The executable migration registry contains 22 ordered migrations and terminates at `0022_aws_data_platform_collector`. PR #198 is absent from local history, no `origin` is configured, and hosted secrets, Actions permissions, workflow runs, and artifacts cannot be inspected. RC1 therefore remains **NO_GO** and publishing remains disabled.

## Framework reconciliation

The existing Beta certification manifest, candidate verifier, release candidate workflow, deployment harnesses, security checks, backup/restore utilities, Helm chart, and product ledger are retained as the single framework. The RC1 work adds registry introspection, validation, bounded dispatch, integrated orchestration, and independent downloaded-evidence verification rather than creating a parallel certification system.

The mandatory producer is `.github/workflows/beta-1-release-candidate.yml`; it supports exact-SHA dispatch, Elasticsearch 9.4.2, Helm and repository gates, hosted kind/upgrade values, backup/restore, seven local image builds, CycloneDX SBOMs, and critical-vulnerability scanning. The integrated orchestration is `.github/workflows/beta-1-integrated-certification.yml`. The expected integrated artifact is `dataobs-beta-1-rc1-integrated-certification`, schema 1.1. AWS collection is optional because no Collection Manager workload is packaged.

## Findings and blockers

* Existing workflows include dispatch, pull-request, push, and reusable `workflow_call` triggers. Only manifest-listed evidence producers are part of the RC contract.
* Hosted requirements are GitHub Actions read/write dispatch permission, external test configuration (`DATAOBS_SMOKE_VALUES`, `DATAOBS_UPGRADE_VALUES`), Elasticsearch 9.4.2, an OIDC test provider, kind/Docker, Chromium/Playwright, Syft, Trivy, Helm, kubectl, and snapshot-repository filesystem access.
* Mandatory evidence must be schema 1.1, `status: pass`, skip-free for mandatory real-stack categories, redaction safe, exact-SHA bound, and independently verified.
* The local baseline cannot prove browser, accessibility, backup/restore, HA/restart, security, build/scan, deployment, upgrade, or rollback execution. These are blockers, never successful or pending-as-pass results.
* Collection Manager has a CLI and AWS collection exists, but it has no supported Helm workload or image and is explicitly excluded from the mandatory package. Migration 0022 remains mandatory.
* Helm and security implementations exist; production readiness and GA are not claimed. Certification depends on hosted evidence.
* Historical evidence and migration definitions are not rewritten. Active release gates must derive the registry terminal dynamically.
