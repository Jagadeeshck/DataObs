# Stream and Pathway Reliability production-closure audit

## Audited baseline

The auditable checkout is `043a4e368d40f0fe04d8d48610b1af613985357b` (merge of PR #212). This container has no Git remote, so fetching `origin` and inspecting hosted PR metadata was impossible; the merge commit for PR #208 (`b8e6289`) and every file in its first-parent diff were inspected locally. The merge-marker guard passed. The executable registry dynamically reported `0024_job_run_reliability_runtime`; therefore the correction is forward-only migration `0025_stream_pathway_reliability_production_closure`, depending on 0024. Migrations 0023 and 0024 are unchanged.

No Elasticsearch service is available in this checkout. Consequently 9.4.2 migration application and live mapping inspection remain hosted acceptance gates, not locally claimed certification.

## Confirmed defects and acceptance matrix

| Requirement | Current implementation | Test proving current state | Gap | Planned correction |
| --- | --- | --- | --- | --- |
| Status projection | Read-only projection addressed by definition ID | `tests/stream_360/test_reliability_runtime.py` | Worker never wrote status; ID was cross-scope unsafe | Scope-hash ID and OCC projection after evaluation |
| Write order | Evaluation then checkpoint | runtime ordering test | No status or signal stage | evaluation → projection → signal → checkpoint → health |
| Signals | Repository method unused | source audit | No transition state machine | deterministic breach/recovery signals |
| Runtime health | API fabricated zeros | route source audit | Nothing persisted | persist cycle health and read durable state |
| Lease | scripted acquire; basic fence read | source audit | no bounded expiry/heartbeat during batch | retain fencing checks; renewal/long-batch certification remains open |
| Elasticsearch OCC | definition/status used overwrite | source audit | application revision was not OCC | `_seq_no`/`_primary_term` guarded projection/checkpoint |
| Trusted scope | arbitrary environment header | route source audit | caller could select environment | use authenticated `request.state.environment` |
| Trusted actor | assumed mapping principal | route source audit | real principal is an object | require `principal.subject`, fail closed |
| Pagination | always null cursor | route source audit | no query-bound signed cursor | remains a documented production blocker |
| Strict mappings | 0023 generic resources only | migration plan audit | writer fields/template retention absent | additive mappings and strict component templates in 0025 |
| Data streams/retention | generic templates, retention prose | registry audit | no attached lifecycle policies | 90-day evaluations, 365-day signals |
| Observation adapters | latest projections used broadly | source audit | historical metrics lack bounded series | remains a documented production blocker |
| Resource 360 | reliability console only | PR #208 file audit | no five-page integration | remains a documented production blocker |
| Exact commit evidence | workflow reference only | ledger audit | no retained run | keep `functional_unvalidated` |

## Design and rollback

Every mutation verifies the lease fence. An append-only deterministic evaluation is the reconciliation anchor. Status is then created or replaced with Elasticsearch OCC, a deterministic transition signal is created when entering breach or completing recovery, and only then is the definition checkpoint advanced to an explicit UTC timestamp. Cycle health is persisted last. A failed stage prevents checkpoint advancement; duplicate append-only documents are safe reconciliation anchors. Signal IDs make retries idempotent.

Before rollback, stop workers, snapshot mutable definitions/status/runtime state, and retain append-only evaluations for 90 days and signals for 365 days. Remove the 0025 templates or policies only after retention review. Migrations 0023–0025 remain recorded; rollback is operational, never migration-file mutation.

## Known limitations

This local closure does not claim production certification. Signed cursor pagination, complete resource-specific time-series observation adapters, five Resource 360 integrations, production CLI composition, lease renewal during long batches, full Console acceptance, and retained exact-SHA Elasticsearch/browser/accessibility evidence remain required before release readiness can move from blocked.
