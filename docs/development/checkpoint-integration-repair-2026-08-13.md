# Checkpoint integration repair — 2026-08-13

## Preflight and decision

- **Audited base:** `e9dfa5ddcbc5bc7dfd04ea0112d914b69c9d60dc` (merge PR #283, Team 1 stream capacity planning).
- **Remote state:** the supplied checkout had no `origin`; fetch/pull and live comparison were therefore unavailable. The audited base exactly matches the task's audited `main` SHA.
- **Branch:** `codex/checkpoint-integration-repair-2026-08-13`.
- **Application / chart:** `0.2.0` / `0.2.0`.
- **Terminal migration:** `0033_team1_stream_schema_intelligence_runtime` (33 migrations, one leaf).
- **Release decision:** **NO_GO**. `supported: []` and security posture **INCOMPLETE** remain unchanged.

## Repairs

Quality routes, search and investigation ownership now resolve to Team 2; Job dashboard ownership resolves to Team 2; Incident dashboard ownership resolves to Team 3. Regression tests cover each mapping. The integrated Console production build exposed and this checkpoint repaired Quality API typing/export drift, evidence-envelope fields, strict optional coverage handling, route-test portability, and Investigation union access. Test-package markers repair pytest basename collisions without weakening discovery.

The stable Team delivery foundation remains the universal PR/push gate. Its reusable backend job now runs team boundaries, generated/docs/ledger checks, migration graph/release/Helm checks, route permissions and workflow-security validation. Its Console job now includes navigation, visualization and performance checks. The backend evidence writer no longer converts its own `independent_verification_result` from pending to passed.

Canonical ledger audit metadata and current product baseline now cover the integrated state through PR #283. Release/Helm terminal migration references are synchronized. Historical audits and retained artifact evidence were not reinterpreted as hosted certification.

## GitHub Actions diagnosis

`gh auth status` reports no authenticated GitHub host, and the checkout has no configured remote. Unauthenticated API requests could not read private repository settings. Workflow YAML is valid and the stable integration gate has `pull_request`, `push` to `main`, and `workflow_dispatch` triggers. No hosted run is claimed.

### P0 external repository setting

An administrator must open **Repository Settings → Actions → General**, enable Actions for the repository, permit the actions used by these workflows, and set workflow token permissions to read-only by default. Then configure the branch ruleset for `main` to require the stable **Team delivery foundation / backend** and **Team delivery foundation / console** checks, dispatch the workflow, and retain the resulting exact-SHA artifacts. The administrator must also confirm rulesets do not require check names that no active workflow emits. This setting could not be inspected or changed without repository authentication.

PR #162 could not be inspected, commented on or closed without authentication. It remains an external hygiene action; if still open and obsolete, close it with the factual supersession explanation requested by the checkpoint.

## Validation evidence

Local output is local validation only, never hosted certification.

| Check | Command | Result | Evidence | Fixed? | External blocker? |
|---|---|---|---|---|---|
| Migration graph | `python scripts/release/validate_migration_graph.py` | pass | 33 migrations; one terminal leaf | yes | no |
| Terminal helper | `python scripts/release/current_terminal_migration.py --json` | pass | terminal `0033_team1_stream_schema_intelligence_runtime` | yes | no |
| Release metadata | `python scripts/release/check_release_metadata.py` | pass after repair | executable terminal synchronized | yes | no |
| Helm metadata | `python scripts/release/check_helm_migration_consistency.py` | pass after repair | default and production values synchronized | yes | no |
| Workflow security | `python scripts/security/validate_workflow_security.py` | pass | zero findings | yes | no |
| Console unit tests | `pnpm test` | pass | 23 files, 138 tests | yes | no |
| Console build | `pnpm build` | pass | Vite production build completed | yes | no |
| Console bundle | `pnpm bundle:check` | pass | 739.5 KiB gzip JavaScript | yes | no |
| Console performance | `pnpm performance:check` | pass | bounded raw totals/chunks | yes | no |
| Browser/axe | `pnpm playwright` | `blocked_external` | Chromium executable absent; 15 tests could not launch | no | yes |
| Python compile | `python -m compileall -q src packages services integrations tests scripts` | pass with one existing `finally` syntax warning | compilation completed | no | no |
| Ruff/Black | `ruff check .` / `black --check .` | pass after formatting repair | repository style synchronized | yes | no |
| Full pytest | `pytest -q` | pass after packaging/integration expectation repairs | 1,202 passed, 160 skipped (external opt-ins) | yes | no |
| Actions execution | `gh workflow list`; `gh run list --limit 50` | blocked | no GitHub authentication | no | yes |

## Security and hosted blockers

Workflow least privilege validates locally with `contents: read`. SECF-002 hosted tenant-isolation evidence and SECF-003 independently verified exact-SHA signature evidence remain absent. Browser, Kubernetes, OIDC, SBOM/provenance/signing, HA/DR, upgrade/rollback and Elasticsearch 9.4.2 hosted certification are not inferred from local checks.

## Final branch identity

The final committed SHA is recorded by the Git commit and PR; this document deliberately does not predict a SHA before its own contents are committed. Changed paths are the commit diff and include Console ownership/build repairs, workflow gates, release metadata, canonical product truth, test packaging, repository formatting closure and this report.
