# Team 5 platform supportability Console v1 audit

Audited base: `39b7757a8cce5634bf84f17da53d745f59eefc6b`. The checkout has no Git remote, so GitHub merged/open PR inspection and pulling `main` were not possible. Local history contains Team 0 PR #268 and Team 5 fleet and visualization merges. Terminal migration is `0032_team2_data_slo_production_runtime`.

| Section               | API                                          | Permission                 | Data owner | Bounded                   | Sensitive             | Console treatment                                    |
| --------------------- | -------------------------------------------- | -------------------------- | ---------- | ------------------------- | --------------------- | ---------------------------------------------------- |
| support               | `GET /api/v1/platform/support`               | `platform_operations:read` | Team 0     | fixed fields, 20 blockers | release SHA/freshness | typed support profile; no SLA inference              |
| diagnostics           | `GET /api/v1/platform/diagnostics`           | same                       | Team 0     | fixed checks              | diagnostic detail     | typed reason/remediation codes only                  |
| configuration         | `GET /api/v1/platform/configuration`         | same                       | Team 0     | allowlisted indicators    | fingerprint           | fingerprint metadata only; raw configuration ignored |
| maintenance           | `GET /api/v1/platform/maintenance`           | same                       | Team 0     | fixed fields              | operator reference    | evidence-only schedule language                      |
| known-issues          | `GET /api/v1/platform/known-issues`          | same                       | Team 0     | maximum 100               | issue details         | typed bounded table; optional safe reference         |
| operational-readiness | `GET /api/v1/platform/operational-readiness` | same                       | Team 0     | fixed categories          | evidence references   | authoritative headline, blockers and gate matrix     |

## Adjacent contracts

- Support bundle generation/list/download has no public Console API; no UI action is provided.
- Release readiness is exposed only as `release_decision` in support identity metadata; it is shown separately.
- Runbook registry, escalation matrix, severity definitions, certification, readiness history/events and independent current-production-readiness evidence are not exposed by this API and are not reconstructed from YAML.
- Supportability requests remain platform API requests. The browser neither overrides nor invents tenant scope.
- Team 0 source validators discovered: `validate_supportability_contracts.py`, `validate_runbook_coverage.py`, and `render_current_production_readiness.py`.
