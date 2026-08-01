# Pathway Explorer Console v1 audit

## Confirmed defects and corrections

* Durable pathway definitions omitted the bounded edge objects used to build them, leaving latency and bottleneck intelligence without evidence. New projections retain those bounded edges; topology remains backward compatible with old identifier-only documents.
* Topology returned identifiers only. It now returns embedded edges and bounded node projections while preserving identifiers.
* Stream topology incorrectly treated pathway definitions as edge projections. The Pathway 360 API no longer fabricates edges from that resource; old definitions honestly return an empty edge list.
* Inventory lacked bounded server filters and used an unmapped generic sort. Fixed allowlisted filters and deterministic projection-specific sorting are fingerprinted into cursors.
* SLO optimistic concurrency and tenant/environment reads already existed. The Console exposes review-first draft creation and explicitly handles conflict semantics; automatic remediation is unsupported.

No released migration was changed and no migration was added. Known source limitations are documented in the operations guide.
