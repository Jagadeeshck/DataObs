# Incident idempotency and rolling-upgrade audit

Baseline main SHA: `236bd43` (merge of PR #105). Migrations 0001–0012 are present and unchanged; no 0013 storage requirement exists.

| Concern | PR #105 behaviour | Correct behaviour | Implementation | Test evidence |
|---|---|---|---|---|
| Incident-ID compatibility | Environment was added twice | Stable v1 tenant + dedup formula | Named `incident_id` helper | `test_incident_id_matches_pre_0012_contract` |
| Finding-ID semantics | Deterministic source identity | Corrections keep ID | Existing source/version formula; immutable scope | focused repository tests |
| Exact replay | OCC update | Return without write | pure unchanged decision | `test_exact_replay_performs_zero_updates_and_preserves_sequence` |
| Corrected/newer replay | Projection stayed stale | Refresh without occurrence | `decide_finding_merge` | `test_newer_replay_refreshes_projection_without_occurrence` |
| Stale replay | Unspecified | Cannot regress | stale no-op decision | `test_exact_and_stale_replays_are_noops` |
| Occurrence counting | Unique IDs only, but replay wrote | Increment only new ID | sorted set plus explicit flag | merge unit tests |
| Affected-assets refresh | Only new finding | Monotonic enrichment | sorted union on every merge | `test_stale_replay_can_only_enrich_assets` |
| Evidence refresh | Only new finding | newest wins; missing may fill | timestamp precedence | newer/stale tests |
| Severity refresh | Only new finding | deterministic on relevant mutation | severity calculator on occurrence/newer projection | merge tests |
| Create conflict | Bounded retry | Re-read winner and decide | service retry loop | focused conflict tests |
| Update conflict | Blind retry | Re-read and stop if equivalent | decision before each update | exact no-write test |
| Rolling deployment | Different IDs possible | One stable create target | v1 helper | compatibility test |
| Retry exhaustion | Domain conflict/409 | Preserve finding and redact | save precedes bounded loop | API OCC tests |
| Sequence-number behaviour | Exact replay advanced it | No-op keeps `_seq_no` | update only when changed | unit and ES integration evidence |
| Hosted CI evidence | ES 9.4.2 gate existed | Upload replay/concurrency evidence with no softened failure | workflow gate | Hosted URL/artefacts pending; do not claim pass |

## PR #105 review closure

The three remaining findings are addressed respectively by the stable named ID helper, replay-aware pure merge decision, and early no-write return. This audit does not claim old review threads are resolved or hosted CI passed; reviewers should close them only after reviewing this PR and its hosted artifacts.
