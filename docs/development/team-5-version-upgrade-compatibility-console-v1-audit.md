# Team 5 version upgrade and compatibility Console v1 audit

## Scope and base

Audited base: `ad31a9a38d69dd98b2191318b331a7134f5339e4` (merge of PR #275). The local checkout has no configured Git remote, so a network pull and open-PR inspection could not be performed. Local merge history after Team 5 PR #272 includes PRs #273, #274, and #275; #274/#275 reconcile schema migration registration. The migration DAG validator reports 33 migrations and terminal `0033_team1_stream_schema_intelligence_runtime`. The canonical terminal helper and Helm consistency checker currently fail with `NameError: migrations is not defined`; the Console therefore never embeds that value.

## Backend contract audit

| Capability                                  | Backend owner          | API available                                    | UI v1                                           | Mutation  |
| ------------------------------------------- | ---------------------- | ------------------------------------------------ | ----------------------------------------------- | --------- |
| Compatibility policy/matrix                 | Team 0                 | `GET /api/v1/platform/compatibility`             | Matrix and release state                        | None      |
| Upgrade assessment                          | Team 0                 | `GET /api/v1/platform/upgrade-readiness?target=` | Readiness, reasons, rollback, plan              | None      |
| Version/deprecation policy                  | Team 0                 | Partial / deprecations absent                    | Explicit unknown where absent                   | None      |
| Migration DAG/terminal/immutability         | Team 0 release tooling | Not in Console API                               | Explicit unknown; no guess                      | None      |
| Helm consistency                            | Team 0 release tooling | Not in Console API                               | Explicit unknown                                | None      |
| Schema/OpenAPI/config compatibility         | Team 0                 | Not separate in current response                 | Render dimension if supplied, otherwise unknown | None      |
| Release/operational readiness/certification | Team 0                 | Separate supportability APIs                     | Distinct rows and handoff                       | None      |
| Deployment/rollback execution               | Team 0 operations      | Mutation endpoints exist elsewhere               | Excluded                                        | **Never** |

| Check                                | Authoritative source                   | Pass/fail/unknown                                               | Blocking                        | Console treatment                                |
| ------------------------------------ | -------------------------------------- | --------------------------------------------------------------- | ------------------------------- | ------------------------------------------------ |
| Dimension compatibility              | compatibility `dimensions[].state`     | supported / compatible-but-unvalidated / incompatible / unknown | Only explicit incompatible      | Independent matrix row                           |
| Upgrade readiness                    | readiness `readiness`                  | ready / warning / blocked / unknown                             | Explicit blocked                | Prominent headline; not recomputed               |
| Predecessor                          | `previous_dataobs` dimension           | backend enum                                                    | Backend policy                  | Highly visible, unknown preserved                |
| Rollback                             | `rollback_classification`              | backend enum                                                    | Backend reason codes            | Prominent classification, never an action        |
| Migration/Helm/schema/OpenAPI/config | API dimension or missing               | backend state / unknown                                         | Backend only                    | No browser calculation; missing means unknown    |
| Evidence freshness                   | evaluated timestamp (currently absent) | current / stale / unknown                                       | Backend only                    | Unknown, never converts old pass to current pass |
| Release decision                     | supportability API (separate)          | GO / NO_GO / unknown                                            | NO_GO is blocking in its domain | Separate handoff; never inferred                 |

## Findings

The compatibility endpoint returns the current DataObs version, release state, and policy dimension entries. The readiness endpoint requires a target and returns current/target versions, readiness, reason codes, rollback classification, and an ordered plan. It does not expose profiles, blocker severity, evidence timestamps, migration graph details, terminal migration, Helm consistency, deprecations, API/schema diff results, certification, or release decision. UI v1 fails closed by describing these as unknown rather than synthesising them. `assess_upgrade` remains wholly backend-owned.
