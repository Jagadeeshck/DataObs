# Team 0 Sprint 3 v0.2.0 release-gate audit

Assessment: 2026-10-29.

## Integrated baseline

- Starting main: `855345eb02250f9a738abe44bd520247243032bf`
- Sprint branch: `codex/sprint3-team0-release-gates`
- Release target: DataObs `v0.2.0`
- Candidate target if Gate 0 succeeds: `0.2.0-rc.1`
- Release decision: `NO_GO`
- Candidate frozen: no
- Supported platforms: none
- Released migrations remain immutable. No migration definition or checksum is changed in this sprint.

## Root-cause matrix

| Area | Fresh integrated-main observation | Common root cause | Sprint 3 disposition |
|---|---|---|---|
| Secured migrations | Team 0 security hardening run 40961601016 passed on `855345...` | Earlier Data Product/reliability conflicts were clean-install mapping-ownership defects | Already repaired by merged Team 0/#323. No new migration edit. |
| IAM / tenant isolation | IAM run 40961601069 passed on `855345...` | Earlier legacy rule tenant leakage required authenticated tenant/environment scoping | Already repaired by merged Team 2/#322. Tests remain unchanged and fail-closed. |
| Backup / destructive restore | Run 40961601206 reached real ES indexing after migrations, then ES rejected pipeline id `none` | Data-stream template used a literal nonexistent ingest pipeline rather than the ES no-pipeline sentinel | Team 0 changes `index.default_pipeline` to `_none`; semantic recovery/JUnit verification remains mandatory. |
| MVP smoke | Run 40961601001 reached demo seeding, then strict mapping rejected `overall_health` | Shared mutable projection indices were created from the global union without writer-complete index-owned fields | Team 0 adds narrow clean-install mapping ownership for existing Command Center and pathway-node projections. Strict mappings remain enabled. |
| Kind / Helm | Run 40961600975 passed lint/render/migration immutability; migration job completed; Console healthy; API pod CrashLoopBackOff | Helm API template rendered duplicate security/CORS env entries; retained diagnostics omitted pod logs/events, hiding the remaining crash cause | Duplicates removed; Kind failure artifact now records events plus current/previous API/Console logs. No timeout increase or readiness weakening. |
| Shared Python / OCC | Main CI and Foundation failed Black 26.10.1 before deeper assertions | Formatting drift in recently merged isolation/mapping regressions | Team 0 applies format-only corrections. No assertions removed. |
| Console | Main CI/Foundation/browser stopped at Prettier on three E2E files | Team 5-owned formatter drift | Team 5 Sprint 3 PR #328 owns the exact three files. Team 0 does not duplicate UI changes; final integrated SHA must contain #328 and pass Console Beta independent verification. |
| Kafka certification | Main CI could not pull `bitnami/kafka:3.9`; diagnostics then missed their output directory | Invalid certification image contract plus brittle failure capture | Team 0 uses the repository-standard official `apache/kafka:3.9.1`, external listener for host tests, and fail-safe diagnostics directory creation. |
| Certification ES/Postgres/Kafka host access | ES container was healthy in security/product profiles while `127.0.0.1:19200` was unreachable and Compose showed no published port | Host-run certification expected loopback access from services attached only to Compose `internal: true` networks | Team 0 adds a dedicated loopback host-access bridge only to intentionally published certification services; internal data/control/denied networks remain internal. |
| Supply chain | Production image security and SBOM passed on integrated main | No current shared defect | Mandatory Gate 0 requirement retained. |

## Guardrails

The sprint does not add product features, rewrite released migrations, weaken strict mappings, relax tenant isolation, skip required tests, convert skipped tests to pass, expand public service exposure, increase Kind timeouts to hide crashes, or manually change `NO_GO`.

## Candidate rule

A candidate may be frozen only after the final integrated exact SHA has successful retained evidence for every canonical Gate 0 producer and `scripts/release/gate0.py verify` returns `GATE_0_GREEN`. Any subsequent source change invalidates that exact-SHA evidence and requires a complete rerun.
