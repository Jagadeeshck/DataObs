# Hosted CI failure matrix — 2026-08-13

## Scope and evidence boundary

The investigated main commit is `2ae26a4a840605b22513cb9d2defdc9979445975` (the merge of PR #288).
The implementation environment has no Git remote or GitHub credential, and the private repository returns `404`
through the unauthenticated Actions API. Therefore the initial failing-workflow count and complete job-log inventory
cannot be independently observed here. This matrix records only first failures supplied for that exact SHA; it does
not invent conclusions for inaccessible runs. The hosted canaries remain unexecuted until this branch is pushed.

| Workflow | Job | Failed step | Failure signature | Root cause | Shared root cause ID | Fix included in this PR? | Remaining blocker | Release blocking? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Team Delivery Foundation | backend validation | Black | `tests/test_settings.py would be reformatted` | Repository formatting and combined diagnostics | CI-FMT | Yes: format is preserved and Ruff, Black, Mypy, and Pytest are separate named steps | Hosted canary not run | Yes |
| Team Delivery Foundation | console validation | high-severity dependency audit | vulnerable transitive `js-yaml` selected below the currently patched `4.3.1` | Scoped override took precedence over the safe global resolution | CI-CONSOLE-AUDIT | Yes: deterministic `4.3.1` override and regenerated frozen lockfile | Hosted canary not run | Yes |
| IAM OIDC and tenant security | `iam-security` | migration immutability | `HEAD^` unavailable after shallow checkout | Insufficient Git history | CI-GIT-HISTORY | Yes: full history for IAM and every migration-immutability caller | Hosted canary not run | Yes |
| Kafka Cluster 360 Console v1 | `verify` | apply migrations | `elastic_transport.ConnectionError` / `RemoteDisconnected` after service health passed | Service health did not prove application-client readiness | CI-ES-READINESS | Yes: bounded helper immediately precedes application interaction; all Elasticsearch 9.4.2 jobs are covered | Hosted canary not run | Yes |
| Team 4 RabbitMQ messaging collector v1 | `validate` | Pytest collection | `ModuleNotFoundError: pydantic` / `ModuleNotFoundError: elasticsearch` | CI tooling installed without runtime dependencies | CI-PY-DEPS | Yes: canonical runtime plus CI requirement bootstrap | Hosted canary not run | Yes |

## Shared fixes and regression coverage

- **CI-FMT:** Backend quality phases are independently named so formatting cannot hide Mypy. Repository-wide Black
  remains mandatory.
- **CI-CONSOLE-AUDIT:** Both the Redocly edge and global `js-yaml` graph are pinned to `4.3.1`; the lockfile has no
  older `js-yaml` package. The reusable Console workflow still runs `pnpm audit --audit-level high` without ignores.
- **CI-PY-DEPS:** Product tests that use `requirements-ci.txt` are semantically required to install
  `requirements.txt` as well. CI-only static jobs remain permitted to install tooling alone.
- **CI-GIT-HISTORY:** Every checkout in a migration-immutability workflow fetches complete history. Missing or invalid
  bases continue to fail in the unchanged checker.
- **CI-ES-READINESS:** Every job launching Elasticsearch 9.4.2 and running repository tests or migration checks calls
  the bounded readiness helper first. The helper retries transient disconnects and validates both cluster health and
  the indices API. No startup sleep or `continue-on-error` replaces the gate.

## Canary and release status

| Canary | Status | Evidence |
| --- | --- | --- |
| Team Delivery Foundation backend | **NOT RUN** | Requires hosted branch execution |
| Team Delivery Foundation console | **NOT RUN** | Requires hosted branch execution |
| IAM | **NOT RUN** | Requires hosted branch execution |
| Cluster 360 | **NOT RUN** | Requires hosted branch execution |
| RabbitMQ | **NOT RUN** | Requires hosted branch execution |

- **Production readiness:** `NO_GO`.
- **Security posture:** `INCOMPLETE`.
- **Supported production platforms:** `[]`.
- **Independent verification:** `false`.

Local validation is diagnostic only and is not promoted into hosted, certification, or independent evidence.
