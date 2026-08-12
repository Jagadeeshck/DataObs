# Team 1 stream-to-Data-Product impact

Team 1 exposes scoped stream/pathway binding and Product Exposure evidence through a pure domain contract and a
narrow `DataProductReadPort`. Team 2 remains authoritative for definitions, reviewed membership, dependencies,
Business Criticality, ownership, and SLOs. Team 1 never writes Team 2 indices.

## Semantics and authority

Evidence preference is reviewed active membership, declared output (including `kafka_topic`), explicit dependency,
lineage, pathway/resource, observed application, deterministic correlation, then inference. Multi-broker resources use
`messaging_system`, `resource_kind`, `canonical_resource_id`, and optional `provider_resource_id`; name equality is not a
binding. Every binding retains its method, confidence, coverage, time, and evidence references.

The state machine is `linked` → `potentially_exposed` → `observed_degradation` → `slo_impact_observed`, with
`recovering`, `unknown`, and `unavailable`. A degraded upstream plus a downstream relationship produces only Potential
Exposure. Independent product evidence is required for Observed Product Degradation, and a failed SLO must have a
clear stream component relation to establish Product SLO Impact. No state claims causation.

## Scores and bounds

The optional exposure score weights authoritative criticality 25%, relationship strength 20%, graph distance 10%,
upstream degradation 15%, related SLO evidence 20%, and source coverage 10%. Missing inputs are removed and remaining
weights renormalized. Confidence is separately the mean of available binding strength, source coverage, topology
completeness, freshness, SLO coverage, and lineage availability; criticality never raises confidence.

Defaults are depth 5, 50 products, 500 edges, and 100 consumers. Absolute bounds are depth 8, 200 products per anchor,
1,000 edges, 500 consumers, and 50 evidence references. Dependency traversal delegates to Team 2's bounded public
service and reports truncation, cycles, and reached depth.

Current v1 resolves on read. No new durable projection or migration is introduced; therefore historical binding views
honestly report `history_unavailable`. A future projection may use Team 1 indices only, append immutable evaluations,
and update current documents with Elasticsearch OCC.
