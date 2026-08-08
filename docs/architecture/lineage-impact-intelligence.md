# Lineage impact intelligence

Lineage intelligence reuses the `0021` graph and canonical asset identity. Production reads cross the typed Team 2 repository boundary. Elasticsearch traversal issues one tenant-and-environment-scoped adjacency query per bounded frontier; it never scans the tenant graph. This pattern uses stable `terms` filters supported by Elasticsearch 9.4.2, deterministic sorting, application-side cycle tracking, and hard depth/node/edge/path limits.

Impact means **potential structural exposure**, not confirmed failure or root cause. Direct and transitive entities retain shortest distance, paths, confidence, reason codes, and contextual warnings. The score is `100 * weighted_mean(available bounded components)`. Base weights are change severity 30%, relationship 20%, distance 20%, path confidence 20%, and criticality 10%; weights are normalized over available values, measured zero is retained, and confidence remains separate.

Stale edges are excluded by default and disclosed when included. Explicit tombstones may deactivate current edges, but historical observations remain immutable. A truncated result has `partial` status and cannot represent a complete blast radius.
