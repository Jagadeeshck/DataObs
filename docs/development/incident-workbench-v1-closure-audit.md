# Incident Workbench v1 closure audit

Audited baseline: `232a8e073cbfedf0d0c2444e9be23b59e959a4ee` (the newest locally supplied main snapshot), before edits. A fetch of `origin/main` was attempted on 2026-08-01 but GitHub required credentials unavailable in this environment. PR #187's complete patch was audited from local merge `43ec068`; remote review-thread text could not be retrieved, so this document does not claim that inaccessible comments were read.

Subsequent local merges through #197 were inspected. Security work in #192/#193/#196 establishes `request.state.principal`; Console merge/conflict work through #195 preserves incident registration. This closure does not edit security, route registry, Console routes, migrations, or shared Elastic-store code.

## Findings verified on the baseline

| PR #187 finding | Current-main verification | Closure implementation/test | Status |
|---|---|---|---|
| Timeline documents violate the released strict stream mapping | Present: the repository indexed the API dictionary and sorted unmapped `timestamp`/`event_id`. | Explicit bidirectional storage adapter; generated-mapping contract test. | Closed in unit scope; real Elasticsearch certification pending. |
| Filtering/sorting occurs after a bounded 200-document read | Present: workbench called `list_incidents`, filtered and sorted in Python. | Typed repository inbox query applies scope and all representable filters server-side; >200 keyset test. | Closed. |
| Mutable offset cursor instead of `search_after` | Present: unsigned base64 `{i,q}` offset sliced a newly sorted list. | Existing signed cursor codec plus PIT ID and final sort tuple; keyset-equivalent memory repository. | Closed. |
| Actor comes from the wrong request-state attribute | Present: route read `request.state.subject` with `authenticated-user` fallback. | Fail-closed helper reads `request.state.principal.subject`; focused test proves the real attribute and missing-principal response; no generic fallback. | Closed. |

## Certification boundary

No released migration or checksum changed and no migration was added. The incident/comment stream, action-idempotency resource, and mapped `metadata`, `correlation_id`, `event_type`, `revision`, scope, request and summary fields are reused. Source/finding-type filtering is not advertised because the incident projection does not retain a mapped source type. Deterministic operation evidence permits retry reconciliation after a timeline append failure; Elasticsearch provides no cross-document transaction and this patch does not claim otherwise.
