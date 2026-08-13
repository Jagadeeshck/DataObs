# Team 0 platform supportability and operations v1 audit

Audited the clean `main` snapshot at `96d6e4fc0e20d11ee7dcaca5f681660d5dd2be52` before creating the work branch. The executable registry was inspected with `python scripts/release/current_terminal_migration.py --json`; its terminal is `0031_team3_post_incident_review_analytics` (31 ordered migrations). No released migration is changed by this work.

## Canonical release facts

- Application and Helm chart version: `0.2.0` / `0.2.0` from `helm/dataobs/Chart.yaml`.
- Current authoritative release decision: `NO_GO`; retained evidence reports missing certification, recovery, redaction, security, isolation, artifact and vulnerability checks.
- Supported-platform state: none. Kubernetes 1.30 is only the narrow unvalidated candidate; HA is unsupported.
- Active-readiness drift: the checked-in active document incorrectly named migration `0030_team1_multi_broker_messaging_runtime`; executable main had advanced to `0031_team3_post_incident_review_analytics`.

## Existing Team 0 implementation reused

- Platform operations: the authenticated `GET /api/v1/platform/{section}` route, permission `platform_operations:read`, security audit event `platform.operations.viewed`, and sections health, components, workers, migrations, backups, release, SLOs and error budgets.
- Health/readiness: bounded health contracts, cached probes, `/livez`, `/startupz`, `/readyz`, migration readiness and telemetry state. Maintenance did not exist and must not override these results.
- SLO/error budgets and alerts: `src/platform_operations/slo.py`, platform SLO YAML, metrics, and the Team 0 platform alert registry.
- Runbooks: the existing operations library includes Elasticsearch outage/overload, OIDC outage, telemetry outage, migration, backup/restore, Kubernetes policy, release integrity, worker stall, and privileged-access procedures.
- Support bundle: `scripts/operations/collect_support_bundle.py` already provides local-only, JSON allowlist collection, deterministic member metadata, redaction, per-file and total bounds. Its manifest was v1 and redaction findings lacked safe fingerprints.
- Lifecycle/release: `/api/v1/platform-lifecycle/*`, lifecycle models/service/repository, release manifests, release gate YAML, candidate verifier and the single `release_decision.py` authority.
- Diagnostics: health, migration status, worker/release/backup section placeholders and telemetry existed, but there was no common diagnostic contract.
- Redaction: support-bundle key redaction, logging sanitization/security tests and bounded metric attributes existed.
- Correlation/audit: middleware validates or generates `X-Request-ID`, returns it on responses, and platform reads append security audit events with the safe ID.
- Ownership: alert owners and Team 0–5 development handoffs existed, but no deterministic cross-team escalation matrix existed.

## Gaps retained as gaps

Hosted exact-SHA Kubernetes, secured Elasticsearch, OIDC, backup/restore, HA, capacity, browser, supply-chain and production certification evidence is absent or stale. Worker, backup, migration-applied and dependency connectivity observations are installation runtime facts and cannot be inferred from repository state. Therefore missing evidence remains `unknown`, `unvalidated`, `blocked`, or `unsupported`; it is never promoted to supported/healthy. No commercial response commitments or individual contacts were found or added.
