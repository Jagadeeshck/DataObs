# Team 0 hosted CI repair — 2026-08-13

## Trigger and preflight

GitHub Actions began producing real hosted runs after repository Actions configuration was corrected. The starting
`main` snapshot was `ab84da5` and the active terminal migration was
`0033_team1_stream_schema_intelligence_runtime`. Workflows consistently target Python 3.12 for the repaired shared
path, Node 22, pnpm 10.28.1, and Elasticsearch 9.4.2.

This checkout has no remote and no authenticated GitHub CLI session. The public Actions API was rate limited (HTTP
403), so the run total, conclusion counts, raw logs, and post-change hosted canary results could not be independently
retrieved here. They remain an explicit maintainer canary requirement rather than being represented as successful.

## Initial failure inventory

| Workflow | Job | Failed step | Root cause | Shared? |
| --- | --- | --- | --- | --- |
| Team delivery foundation | backend | dependency install | reusable workflow named nonexistent `requirements-dev.txt` | yes |
| Azure data platform collector | validate | pytest | test runner absent from installed dependency set | yes |
| Console validation callers | console | `pnpm api:generate` | repository-wide `js-yaml` override was incompatible with Redocly 1.x | yes |
| Migration-dependent callers | validation | migration immutability | shallow checkout did not contain the requested base | yes |
| Elasticsearch-backed jobs | migrations/tests | first ES request | service container had not reached cluster readiness | yes |

These bootstrap defects cascade through reusable workflow callers; they are not evidence of five independent product
defects.

## Repairs and version decisions

`requirements-ci.txt` is now the canonical CI tooling layer installed alongside `requirements.txt`. The reusable
backend workflow owns this bootstrap, and Azure uses the same layer plus its provider dependencies. No test was made
optional. History-dependent Azure checkout now fetches full history; the reusable backend already did so. Existing
event-aware `scripts/resolve_ci_base.py` remains the preferred base-SHA resolver, and invalid refs continue to fail.

Console retains Node 22, pnpm 10.28.1, openapi-typescript 7.13.0, frozen installs, and generated-code diff enforcement.
The root cause was dependency override drift: `@redocly/openapi-core` 1.x expects the `js-yaml` 4.1 API while the broad
security override forced 4.3.1. Redocly is pinned to 1.34.19 and receives a narrowly scoped `js-yaml` 4.1.0 override;
the repository-wide override remains in force for other consumers.

`scripts/ci/wait_for_elasticsearch.py` polls cluster health until yellow/green with configurable URL, credentials, TLS
verification, timeout, and interval. It emits attempt diagnostics and exits non-zero on timeout. The shared backend,
beta security, and backup/restore foundations now wait before migrations or tests; no blind sleep or skip is used.

## Security and release invariants

This repair does not change product behavior, migration immutability, tenant isolation, exact-SHA/checksum evidence,
artifact boundaries, or release authority. Historical root reports remain invalid as runtime evidence. Same-run
integrity is not independent verification. Only security `PASS` may authorize; `INCOMPLETE`, `UNVALIDATED`, and `FAIL`
remain blocking.

Current truth remains: production readiness **NO_GO**; supported production platforms `[]`; security posture
**INCOMPLETE**; hosted evidence insufficient; independent verification `0 / false`; SECF002 and SECF003 open.

## Validation, canaries, and remaining failures

Local validation covers YAML parsing, requirement references, bootstrap ordering, pinned Console setup, generated-code
ordering, ES readiness ordering, and fail-closed timeout. Console generation was reproduced failing before the scoped
override and succeeding after it. Full command outcomes belong in the pull request validation section.

Hosted canaries remain **not run from this unauthenticated checkout**: Team delivery backend/Console, Team 0 security,
beta security, Console Product Experience, one ES certification workflow, and Azure collector. Do not claim CI healthy
or merge until maintainers run that bounded set. Any later failures must be classified as product, CI, configuration,
secret, external dependency, or runner/tooling; missing mandatory external evidence blocks release.
