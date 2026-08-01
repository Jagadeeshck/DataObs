# Pathway Explorer Console

Pathway Explorer reads durable, tenant- and environment-scoped pathway projections. Inventory queries are bounded to 200 records, use deterministic `pathway_id`/`_id` ordering, fixed source allowlists, and cursors fingerprinted to route, environment, filters, and sorting.

## Evidence semantics

Measured values take precedence over derived, inferred, and correlated evidence. Zero is a measurement; absence is rendered as unavailable. `data_status`, timestamps, confidence, coverage, warnings, missing inputs, reason codes, and request IDs travel with the evidence. Partial topology means observation coverage is incomplete. Truncation additionally reports the bounded excluded-edge count.

Latency is `trace_derived`, `edge_estimate`, or `unavailable`; an edge estimate is never represented as measured end-to-end latency. Bottleneck results are contribution candidates, not root-cause findings. Comparison is limited to one environment and 31 days and cannot establish causality.

The topology graph is an enhancement over its node and edge tables. The tables remain the accessible evidence source and work without graph interaction.
