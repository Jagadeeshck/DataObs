# Pathway investigation and blast radius

Team 1 exposes bounded dependency evidence, not RCA. The pure graph model is nodes plus directed semantic edges. Iterative breadth-first traversal is deterministic, cycle-safe, and bounded by defaults 5 hops/100 nodes/200 edges/100 paths and hard maxima 8/500/1000/500. Every reached entity carries distance, path, relation, minimum path confidence, unioned source coverage/evidence references, and stale/partial propagation. Truncation is always explicit.

`direct`, `transitive`, `associated`, `inferred`, and `unknown` describe evidence strength. Dependency presence never means observed degradation. Reliability, anomaly, retention and failure evidence remain independent overlays, and absent reliability is `no_data`, never healthy. Team 2 enrichment uses only its public API and may be unavailable. Team 3 incident links are associated evidence; Team 3 exclusively owns correlation/RCA.

Bottleneck candidates rank a dimension's share of observed non-negative values. Confidence is the minimum evidence confidence and is reduced for stale, estimated, partial, missing or low-coverage evidence. Wording remains “candidate” or “highest observed contribution,” never cause.
