# Team 3 incident response reliability v1 audit

## Preflight

- `audited_main_sha`: `ad31a9a38d69dd98b2191318b331a7134f5339e4`
- latest merged PR visible in the audited snapshot: #275
- terminal migration: `0033_team1_stream_schema_intelligence_runtime`
- PR #259, #263, and #270 merge history and source changes were inspected. GitHub's review API returned 404 in this unauthenticated workspace; the complete known findings supplied in the task are recorded below. No unverified claim of having retrieved inaccessible comments is made.

## PR #270 closure matrix

| Finding | Closure |
| --- | --- |
| Derived effectiveness class | Model deserialization recomputes the authoritative classifier and rejects contradictions, including failed-provider/verified claims. |
| Derived evidence coverage | Episode validation requires the persisted scalar to equal `evidence.coverage`. |
| Mixed-scope summaries | Summary rejects mixed tenant, environment, or effectiveness-definition version. |
| Scoring-version supersession | Relationship identity no longer contains scoring version; undecided candidates update by revision while decisions remain durable. |
| Canonical failure signature | Recurrence compares canonical failure-signature fingerprints rather than whole-incident similarity flags. |
| Complete exact recurrence typing | Primary asset, rule, Data Product, business service, failure signature, and confirmed root-cause categories are supported; candidates are not authoritative. |
| Verified timing population | Timing samples are restricted to episodes currently classified `verified_effective`. |

## Scope and certification

This change intentionally contains no escalation/staleness orchestration. The canonical Team 2 error-budget and burn functions are imported rather than duplicated. Real Elasticsearch 9.4.2 certification was not run because no cluster was supplied.
