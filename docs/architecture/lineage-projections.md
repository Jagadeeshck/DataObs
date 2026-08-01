# Lineage projections

OpenLineage evidence is append-only. Dataset and column edges use deterministic identifiers and are projected into tenant/environment-scoped current indices by migration `0021_lineage_analysis_explorer`. Omission from a later event never deletes an edge.

The canonical `/api/v1/lineage` read surface bounds depth (10), nodes (1,000), and edges (2,500), detects revisits and cycles, and reports truncation, confidence, coverage, warnings, observation time, and evidence references. Dataset edges are created only for input/output pairs explicitly present on the same event. Column transformations retain a classification and fingerprint, never raw SQL.

Rebuilds replay immutable observations into an empty current projection. Asset 360, Pathways, and Data Products consume the same canonical asset IDs; they do not own a second lineage graph.
