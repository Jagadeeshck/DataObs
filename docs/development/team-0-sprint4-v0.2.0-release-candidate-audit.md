# Team 0 Sprint 4 v0.2.0 release-candidate audit

Assessment: 2026-10-30.

## Integrated baseline

- Audited main: `c3d3dfe63b2d8227612dc867988db268c8b7424f`
- Sprint branch: `codex/sprint4-team0-release-candidate`
- Target: DataObs `v0.2.0`
- Candidate target: `0.2.0-rc.1`
- Release decision: `NO_GO`
- Gate 0: `GATE_0_BLOCKED`
- Candidate frozen: no
- Supported platforms: none
- Terminal migration: `0033_team1_stream_schema_intelligence_runtime`

Released migrations and their checksums are immutable in this sprint.

## Exact-main observations

| Area | Exact-main evidence | State | Sprint 4 disposition |
| --- | --- | --- | --- |
| Elasticsearch migrations | Security run 41120485735, artifact 13008981762 | PASS on audited main | ES 9.4.2; first apply pass; second apply pass; 33 released checksums retained; terminal migration 0033. Must rerun on final candidate SHA. |
| OIDC/JWKS/RBAC/tenant isolation | Security run 41120485735 and IAM run 41120485609 | PASS on audited main | Signed tenant A/B/C isolation, issuer/audience/expiry/JWKS rotation, TLS negative tests, deny-by-default route policy and service identity are covered. Must rerun unchanged on final candidate SHA. |
| Kind/API startup | Deployment run 41120485485, artifact 13008748014 | FAIL | Migration Job completed and Console became healthy; API crashed because packaged runtime imported release-only `scripts.release.current_terminal_migration`. Runtime now derives terminal migration from `packages.elastic_store.manifest`. |
| MVP | Run 41120485543, artifact 13007474274 | FAIL | Same packaged API `ModuleNotFoundError: scripts` after migration/seed progress. Covered by the same Team 0 runtime-boundary fix. |
| Destructive recovery | Run 41120485890, artifact 13008142677 | FAIL after real migration execution | JUnit executed the destructive test without skip; fixture then wrote non-contract field `action` into strict security-event stream. Fixture now uses released `event_action` contract. Snapshot/delete/restore/integrity still require a successful rerun. |
| Foundation | Run 41120485671 | PARTIAL | Console validate passed; backend validate stopped at Black. Shared Python formatting is being repaired only where reproduced. |
| Shared CI | Run 41120485742 | FAIL | Terraform/Helm, Compose validation, documentation truth, certification contracts and image SBOM/security passed. Failures include shared Black drift, certification ES endpoint mismatch and Kafka observer packaging. |
| Certification Elasticsearch | Shared CI certification profiles | FAIL | Compose publishes ES at loopback 19200 while certification migration helper inherited 9200. Helper now defaults to 19200 while explicit workflow overrides remain authoritative. |
| Kafka certification | Shared CI Kafka job, artifact 13009491804 | FAIL | Kafka observer imports `src.telemetry` but its image omitted `src/`; image now packages that explicit runtime dependency. Three-broker KRaft topology remains unchanged. |
| Console/browser | Team 5 Console Product Experience run 41120485477 plus Team 1/2 Console producers | FAIL | Real Playwright failures remain across release/supportability journeys. These are Team 5/browser-owner evidence blockers unless they disappear after shared backend fixes; Team 0 does not weaken browser assertions. |

## Release authority

`scripts/release/gate0.py` remains the Gate 0 authority. Its verifier accepts only same-SHA producer runs and retained evidence and leaves `release_decision=NO_GO` / `candidate_frozen=false` even when Gate 0 becomes green.

The mandatory Team 1–5 capability contract is `docs/release/beta-1-certification-manifest.yaml`. Its mandatory producer evidence is accepted only from `workflow_dispatch`; ordinary push successes are source-health diagnostics only.

`scripts/release/dispatch_beta_certification.py` and `.github/workflows/beta-1-integrated-certification.yml` are the existing bounded domain orchestration path. No competing dispatcher is introduced.

## Supported-platform and publication boundary

The first-supported-platform evidence index and release gates are still PENDING. `supported-platform-matrix.yaml` has `supported: []`. The older protected first-supported-platform workflow deliberately fails closed at sign/verify/install until real protected staging inputs exist. The newer Beta candidate assembly also requires real `security-release-gate.json` and `supported-platform.json` before release authorization.

Therefore source closure may prepare an independently certifiable RC, but it cannot truthfully promote a supported platform or publish v0.2.0 without those protected retained artifacts.

## Acceptance rule

Freeze `0.2.0-rc.1` only after the final integrated SHA has:
1. `GATE_0_GREEN` from `scripts/release/gate0.py verify`;
2. same-SHA mandatory Team 1–5 workflow-dispatch evidence accepted by `verify_beta_candidate.py`;
3. supported-platform evidence independently verified;
4. security release gate PASS;
5. supply-chain/SBOM/provenance/signature/install verification complete.

Any source change after evidence collection invalidates the candidate evidence and requires rerun.
