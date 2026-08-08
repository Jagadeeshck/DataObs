# Pathway investigation, blast radius, and time travel v1 audit

**Audited base:** `70f77d85b17776fe2222d591788f145269479057`  
**Terminal migration before this change:** `0027_platform_environment_tenant_multicluster_lifecycle`  
**Reviewed integrations:** merged PR #225 (`98fb8ab`), PR #227 (`a01db1c`), PR #223 (`b574bd4`), Pathway 360 routes/UI, pathway events, reliability and Stream Intelligence contracts.

| Requirement | Existing evidence | Current gap | Decision |
| --- | --- | --- | --- |
| Historical topology | Append-only `pathway_event` contains edge observations | It cannot prove complete graphs or deletions | Add forward-only snapshots; never back-project current topology |
| Effective timestamps | Edge observations have timestamps | No graph-wide effective time | Store `effective_at` and `observed_at` |
| Deletions/tombstones | Current lifecycle state exists | No complete historical tombstone stream | Represent removals only between trustworthy snapshots |
| Metrics history | Pathway and Kafka metric streams | Not topology history | Bounded metric overlay only |
| Anomaly history | PR #225/stream intelligence evaluation stream, 90d | May not exist for every resource | Preserve `no_data`/missing inputs |
| SLO history | Reliability evaluation evidence | Definitions do not imply evaluations | Query evaluation history; absent is not healthy |
| Retention history | Forecast evaluation stream | Coverage depends on detector inputs | Preserve confidence and source coverage |
| Schema changes | Team 2 public lineage/change API in PR #223 | Cross-team availability is optional | Public bounded enrichment only; no private index access |
| Config changes | Kafka observations and signal evidence | Not uniformly normalized | Timeline when authoritative; otherwise unavailable |
| Connector events | Kafka Connect evidence exists | Restart/config history may be partial | Evidence link only |
| Consumer rebalance | Consumer-group observations exist | Complete membership history is not guaranteed | Mark partial when absent |
| Deployment evidence | Platform lifecycle evidence and related links | No universal pathway binding | Associated evidence only |
| Data-product links | Team 2 public impact API | Provider can time out | Core traversal continues with enrichment unavailable |
| Incident links | Team 3 public incident read contracts | Team 1 must not correlate/write incidents | Associated links only; Team 3 retains RCA semantics |
| Graph boundaries | Pathway definitions contain bounded nodes/edges | Cross-pathway inventory is incomplete | BFS with explicit 8/500/1000/500 hard caps |
| Time-travel feasibility | No complete reconstructable historical graph at base | Current graph cannot be used as historical truth | Migration 0028 starts trustworthy collection forward |
| Exact migration state | Dynamic terminal script returned 0027 | Snapshot resources absent | Add `0028_pathway_investigation_history`; do not alter 0001–0027 |
| Team 5 contract | PR #227 provider has timeout, cancellation and 50-node cap | It calls detail/health/topology separately | New shaped evidence endpoint; provider handoff remains review work |
| Hosted certification | No exact-SHA hosted artifact exists | Local workflow definition is not certification | Ledger remains `functional_unvalidated` |

## Historical truth conclusion

Append-only edge observations are useful evidence but do not establish a complete topology at an instant and cannot prove removal. Therefore no backfill is offered from current topology. Queries before the first trustworthy snapshot return `history_unavailable`. Snapshot diffs may describe known additions/removals only after collection begins.
