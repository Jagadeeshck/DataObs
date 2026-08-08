# Stream anomaly and retention intelligence v1 audit

## Preflight

- **Audited base:** `c5b7dff6573b6fd0ce76122e7112b726c35d431d` (local clean merge of PR #218). The supplied checkout has no `origin` remote, so a newer hosted `main` could not be fetched.
- **Reviewed inheritance:** merge commits for PR #208 (`b8e6289`) and PR #218 (`c5b7dff`) and their reliability contracts, repository, worker, routes, strict mappings and tests.
- **Terminal migration before this change:** `0025_stream_pathway_reliability_production_closure`; the forward-only decision is `0026_stream_anomaly_retention_intelligence` because strict current projections and retained evidence streams do not exist in 0025.
- **Hosted evidence:** unavailable in this checkout. Capability remains `functional_unvalidated`; local execution is not certification.

## Evidence and identifiers

| Resource | Canonical identity | Historical source | Measured now | Inferred/unavailable |
|---|---|---|---|---|
| cluster | `cluster_id` / reliability `resource_id` | broker and inventory observations | replication counts, freshness | leadership frequency depends on retained changes |
| topic | `stream_id`, `topic_name` / `resource_id` | topic/partition observations | throughput, partition bytes, replication | message size when byte/count pairing exists |
| consumer group | `group_id` / `resource_id` | offset observations | lag, partition lag, offset progress | record age without timestamp evidence |
| connector | `connector_id` / `resource_id` | connector/task observations | task state and restarts | throughput/backlog when provider omits metrics |
| pathway | `pathway_id` / `resource_id` | pathway evaluation evidence | latency, coverage, reliability | edge latency where trace evidence is absent |

Historical observations are mandatory for time-series detectors; current projections are not accepted as substitutes. Real zero observations are measurable values. Missing, stale, partial, estimated and inferred evidence remain distinct. Unsupported combinations are rejected by the canonical capability registry. Raw payload analysis, arbitrary DSL and arbitrary connector configuration are unsupported.

## Gaps and decisions

- **Mapping gap:** 0025 has reliability status evidence but no baseline, anomaly, versioned forecast, failure-candidate or intelligence signal projections. Migration 0026 adds strict bounded fields and lifecycle contracts.
- **Pagination gap:** inherited reliability inventory/history currently returns `next_cursor: null`; intelligence inventory must use the shared signed, query-bound cursor codec before it can be advertised as complete.
- **Resource 360 gap:** reliability panels exist, but complete anomaly/forecast/candidate panels are not yet present on every resource page.
- **Historical query gap:** resource-specific adapters must use fixed aliases, source allowlists, bounded ranges, timeouts and deterministic ordering. No user DSL is accepted.
- **Security/privacy:** tenant, environment and actor come only from authenticated request state; payloads, keys, credentials and raw errors are prohibited. Error fingerprints hash bounded normalized classifications. Change overlays say “change observed near anomaly” and never claim causation.
- **Runtime:** the existing reliability lease/fencing and append-before-projection sequence is the integration point. Intelligence must not create a parallel reliability evaluator. Lease renewal, cursor completion and full production worker composition remain explicit known limitations until their end-to-end implementations and hosted evidence exist.

