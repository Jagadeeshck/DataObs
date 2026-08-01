# Pathway intelligence

Pathway intelligence combines metadata-only OpenTelemetry Kafka span evidence,
Kafka observer projections, and OpenLineage evidence into tenant/environment
scoped canonical nodes, current edges, append-only observations, and bounded
pathways. IDs are deterministic; similarly named resources are never joined
without evidence.

Evidence precedence is conservative: `trace_observed`,
`openlineage_observed`, `kafka_metric_observed`, `catalog_declared`,
`structural`, `inferred`, then `unknown`. Inference remains labelled and is not
presented as proof. Multiple sources increase coverage without duplicating an
edge.

Assembly is root-oriented, cycle safe, confidence-filtered, and bounded by hops,
nodes, edges, and pathways. A missing segment, inferred-only segment, or cycle is
reported as partial/truncated rather than silently completed.

Health preserves `unknown` and `not_configured` as distinct from `healthy`.
Critical active edges dominate; missing or stale evidence lowers confidence.
Latency is `trace_derived` only with valid correlation. Independent segment
samples produce `edge_estimate`; percentiles are never added. Bottleneck output
is a comparable-unit contribution, not a root-cause claim.

Unsupported scenarios include raw Kafka message inspection, payload retention,
name-similarity inference, unbounded graph enumeration, cross-tenant links, and
automatic remediation.
