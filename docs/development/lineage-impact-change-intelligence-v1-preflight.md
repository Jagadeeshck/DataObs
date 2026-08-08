# Lineage impact and change intelligence v1 preflight

## Audit record

- Audited `main`: `c5b7dff6573b6fd0ce76122e7112b726c35d431d`. The checkout had no remote configured, so a network fetch or hosted merged-PR inspection was unavailable. The local merge history through PR 218 was inspected before editing.
- Terminal migration before work: `0025_stream_pathway_reliability_production_closure`.
- Lineage foundation: migration `0021_lineage_analysis_explorer` provides dataset and column observation streams, current projections, checkpoints, and transforms. Its released definition is unchanged.
- Dataset and column edges use deterministic `edge_id`, source/target asset identities, optional column identities, job/run evidence, activity, confidence, evidence references, and observation timestamps.
- The OpenLineage writer appends immutable observations and updates current projections. Omission does not deactivate evidence.
- Existing schema resources are `dataobs-schema-current-v1`, `logs-dataobs.schema_snapshot-*`, and `logs-dataobs.schema_change-*`; no row values are retained.
- Existing lineage routes covered asset, column, job, run, impact, and bounded path lookup. The former implementation read `_dataobs_lineage_edges` and `_dataobs_column_lineage_edges` and scanned the complete scoped collection.
- Console `/lineage` was centrally registered for Team 2 with a static explorer. Jobs, Asset 360, Quality, Data Products, and Incidents expose read-only contextual evidence that lineage intelligence may reference but not mutate.
- Route policy supplies `lineage:read` for GET lineage routes and a method-aware analysis permission for writes.
- Existing coverage includes OpenLineage ingestion/projection tests, lineage traversal tests, and `.github/workflows/lineage-analysis-console.yml`.

## Decision and scope

Migration `0026_lineage_impact_change_intelligence` adds only the two append-only resources that have readers and writers in this change. Existing `0021` current graph resources are reused. In scope: typed contracts/repository, bounded frontier traversal, deterministic schema diff, evidence-led scoring, durable impact evaluations, production API wiring, focused tests, and operator documentation. Out of scope: collectors, raw payload/row browsing, autonomous remediation, changes to Quality/Jobs/Data Product/Incident ownership, and any readiness claim.
