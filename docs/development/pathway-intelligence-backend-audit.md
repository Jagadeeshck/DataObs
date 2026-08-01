# Pathway intelligence backend preflight audit

## Existing behaviour

The original pathway worker normalised Kafka messaging spans and wrote one edge
projection plus an event measurement. It used PIT reads, but sorted with
`_shard_doc`, consumed an unbounded number of pages, discarded the PIT cursor,
and advanced `since` to wall-clock time. Consequently, late observations and
source documents left behind by a bounded cycle could be skipped after restart.

Checkpoint state was stored inside the generic checkpoint `document` object and
had neither a durable event position nor a lease/fencing contract. Concurrent
replicas could overwrite one another. Edge fields were duplicated at the top
level and inside an unrestricted nested `document`; no separately modelled
current edge and append-only, replay-idempotent observation contract existed.

## Product/API state

`src/api/app.py` kept Kafka topology, pathways, and pathway SLOs in
`app.state.kafka_dsm`. The pathway list and topology routes were placeholders;
SLO state disappeared on restart and provided revision semantics without
durable optimistic concurrency. Stream detail endpoints are Elasticsearch-backed
in `src/api/stream_routes.py`, although several product subresources remain
generic observer projections rather than pathway intelligence calculations.

## Existing resources

Migration `0005_kafka_stream_pathway_foundation` already provides pathway nodes,
definitions, SLOs, checkpoints, edge/full/internal metrics, and pathway event/SLO
streams. Migration `0006_pathway_asset_360` adds comparisons and bottleneck
metrics. These resources are reused; an additive migration is not required.

## Intelligence gaps addressed

Before this change there was no bounded pathway assembly, explicit evidence
precedence, complete/partial classification, cycle handling, explainable health,
latency-method labelling, safe bottleneck contribution calculation, bounded
window comparison, or typed impact classification. The canonical engine is
extended in `packages/pathways`; no second pathway engine is introduced.

Unsupported by design: Kafka payload inspection, arbitrary span-attribute
retention, automatic remediation, name-similarity edges, and claims of causal
root cause or trace-derived end-to-end latency without correlation evidence.
