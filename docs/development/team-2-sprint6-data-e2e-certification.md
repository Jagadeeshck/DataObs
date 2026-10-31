# Team 2 Sprint 6 — Data Product and End-to-End Certification

**Team:** Team 2 — Data Quality, Jobs and Lineage  
**Target:** v0.2.0  
**Branch:** `codex/sprint6-team2-data-e2e`  
**Starting main:** `eb9dff57820b39c3dd33a98f834498c30f644d89`

## Starting hosted state

| Capability | Run | Result | Sprint 6 disposition |
| --- | ---: | --- | --- |
| Data Quality Monitoring | 41141189152 | PASS including independent verification | Preserve |
| Job/Run backend | 41141189135 | PASS including independent verification | Preserve |
| Data Product foundation | 41141189206 | Real ES 9.5.5, security and unit PASS; contracts fail Black | Format Team 2-owned certification files only |
| Data Product reconciliation | 41141189111 | Real ES 9.5.5, security and unit PASS; contracts fail Black | Same focused formatting correction |
| Team 2 E2E | 41141189113 | ES healthy; Collector readiness probe resets until timeout | Enable the Collector health extension in the canonical integration fixture |
| Quality Console | 41141189097 | Team 2 backend passed; Console static gate stopped at `global.css` Prettier | Team 5 shared Console blocker |
| Lineage Console | 41141189087 | Team 2 backend passed; Console static gate stopped at `global.css` Prettier | Team 5 shared Console blocker |

## Data Product contract correction

Hosted Black 26.10.1 identified only Team 2 certification formatting in:

- `tests/integration/data_products/test_migrations_elasticsearch.py`
- `scripts/certification/verify_team2_sprint4_e2e.py`

The Sprint 6 change applies the emitted canonical formatting without changing the assertions.

The following executable contracts remain mandatory:

- clean install applies every released migration;
- migration state is ready and checksum-complete;
- repeated apply is idempotent;
- upgrade from 0017 through 0018 executes without rewriting legacy evidence;
- `dataobs-reliability-status-v1.observed_value` remains `double`;
- Data Product revision fields remain `integer`;
- Data Product operation IDs remain `keyword`;
- operation-state mapping remains strict;
- tenant/security/reconciliation suites remain unchanged.

No released migration is modified.

## E2E readiness root cause

Run 41141189113 shows:

1. Elasticsearch became green immediately.
2. The integration stack started `otel-collector`.
3. The workflow repeatedly received `curl: (56) Recv failure: Connection reset by peer` from `127.0.0.1:13133` until the 180-second timeout.
4. The Collector fixture mapped port 13133 but did not configure the OpenTelemetry Collector `health_check` extension.

Sprint 6 fixes the canonical test fixture by enabling `health_check` on `0.0.0.0:13133` and registering it under `service.extensions`. The workflow continues to probe the real health endpoint. The verifier is not weakened.

The readiness step also prints scoped Collector or webhook logs before failing, so future bootstrap failures retain direct service evidence.

## Required signal path

The exact-SHA producer must execute, not skip:

```
Quality check
  -> OpenTelemetry
  -> Collector
  -> Elasticsearch
  -> persisted Quality result
  -> canonical Finding
  -> Team 3 incident correlation
  -> deduplicated Incident
  -> delivery outcomes
  -> authenticated API retrieval
```

The independent verifier continues to require zero failures, zero errors and zero skips for both Data Product migration JUnit and signal-path JUnit.

It also requires:

- Elasticsearch exactly 9.5.5;
- exact producer SHA;
- OTel execution/trace correlation;
- replay resolves to the same incident;
- notification replay count remains zero;
- tenant isolation remains enforced;
- partial delivery is represented truthfully;
- evidence is explicitly redaction-safe;
- migration state is unchanged after repeated apply;
- requested mapping types match canonical writer contracts.

## Team 3 boundary

Team 3 remains the owner of incident correlation, deduplication, lifecycle and delivery behavior. Sprint 6 exercises the existing boundary through the canonical Quality runner and integration test; it does not add or fork incident logic.

Any failure inside Team 3 incident semantics is reported with the exact integration assertion and handed to Team 3 rather than patched through a second Team 2 implementation.

## Team 5 dependency

Team 5 follow-up PR #334, **Team 5: Clear Sprint 6 Console quality and browser gates**, starts from the same main SHA and owns the shared `ui/dataobs-console/src/styles/global.css` Prettier blocker reproduced by both Quality and Lineage workflows.

Team 2 does not duplicate that shared CSS correction. This PR should merge after Team 5 #334, then Quality and Lineage certification must be rerun on the rebased exact Team 2 head.

## Release truth

Team 2 stays **NO_GO** until the final head has:

- green Data Product foundation contracts plus existing real-ES/security/unit jobs;
- green Data Product reconciliation contracts plus existing real-ES/security/unit jobs;
- successful exact-SHA `e2e-signal-path` artifact;
- independent E2E verification;
- zero mandatory integration skips;
- Quality and Lineage Console acceptance after Team 5 #334 is present on the branch.

Workflow definitions or previous-SHA evidence are not sufficient.
