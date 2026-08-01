# Team delivery foundation preflight audit

Audited at the PR #183 merge baseline. The merge is present in history as `3bc29f0`; the terminal migration is `0021_lineage_analysis_explorer`.

## Hotspots and conflict risk

`ui/dataobs-console/src/api/client.ts`, `src/api/` route composition, `packages/elastic_store/manifest.py`, `openapi.json`, generated Console schema, root compose files, shared Console components/state, workflows, README, and `docs/product/capability-ledger.yaml` are touched by many capabilities. The API client, migration manifest/checksums, generated schema, capability ledger and CI workflows have the highest merge-conflict and contract risk.

## Existing foundations

Workflows were capability-specific rather than reusable. Certification helpers already include provenance, redaction, manifest building and independent verification under `scripts/certification/`; these must be reused. Feature directories map naturally to streams/pathways, jobs/lineage/quality, incidents/automation, and shell experiences, but formal ownership was absent. Team 0 now owns the migration registry; feature teams propose changes. Generated artifacts are produced by scripts such as `pnpm api:generate` and checked for drift by `scripts/check_generated_artifacts.py`. The capability ledger is manually curated and validated by `scripts/validate_capability_ledger.py`; optional ownership metadata remains backward compatible.

## Gaps addressed

There were no formal six-team boundaries, CODEOWNERS, cross-team contract sequence, ADR threshold, common fixture manifest, Beta release workstream tracking, branch/label conventions, or reusable validation workflows. This foundation supplies them without changing product behavior.
