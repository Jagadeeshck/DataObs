# Adaptive data anomaly detection v1 — preflight

## Repository audit

The audited local `main` is `70f77d85b17776fe2222d591788f145269479057`; an authenticated fetch was attempted on 2026-08-08 but the private remote supplied no credentials. Recent local merge commits #219–#230 were inspected. The terminal migration is `0027_platform_environment_tenant_multicluster_lifecycle`.

The canonical resources are monitor definitions/current projections, definition events, schedules, observations, baseline versions, evaluations, findings, suppressions, recommendations, coverage, checkpoints, and leases in the migration-managed elastic registry. The monitor runtime in `services/monitor_runtime` owns scheduling, fenced execution, observation, history, baseline, evaluation, and checkpointing. No new resource or migration is required: existing JSON evidence mappings can represent aggregate profiles, immutable generations, eligibility and adaptive evaluation fields.

## Existing foundations

`baseline_engine.py`, `cold_start.py`, `confidence.py`, `seasonality.py`, `thresholding.py`, and `robust_statistics.py` supply cold start, bounded confidence, cohort selection, MAD/IQR/quantile calculation and expected ranges. Authoring already has typed threshold and baseline policies; v1 extends that model with static/adaptive/hybrid baseline mode, training window, contamination policy, drift policy, staleness and timezone. Recommendations use the existing proposed/accepted/rejected/deferred workflow. Contracts reference monitor evaluation evidence; detection is not copied into contracts. Schema-change, job/run, incident, and bounded lineage-impact repositories are correlation/context integration points rather than causal claims.

The quality Console uses the central `ui/dataobs-console/src/app/routes.ts` registry, Team 2 permissions, lazy loaders, Quick Find metadata, and the quality API client. Current certification workflows use merge-marker, team-boundary, generated-artifact, documentation, capability, migration, permissions, Python, Elastic, Console and evidence-verification checks.

## Legacy audit and decision

Issue #24 produced `DistributionDriftCheck` and `ElasticsearchBaselineStore`; callers are the quality check registry and compatibility tests. Issue #30 produced `BootstrapAnomalyDetector` and `HistogramBucketDriftDetector`; no production caller was found. `DistributionDriftCheck` is retained as a deprecated compatibility check. `BootstrapAnomalyDetector` is a deterministic deprecated compatibility shim. `ElasticsearchBaselineStore` is fail-closed and can no longer create `dataobs-drift-baselines-{tenant}`. The dynamic `_ensure_index()` production path is removed. Production execution uses the canonical monitor runtime exclusively.

Other `indices.create` calls occur in the migration registry, legacy API/POC/lineage stores and tests; none is invoked by adaptive evaluation. There is no `dataobs-anomaly-baselines-{tenant}` producer. This v1 makes no Elastic ML entitlement mandatory.

## Migration decision

Reuse current observation, baseline-version, evaluation and finding resources. No migration was added because there is no new writer/reader requiring a dedicated index and released migrations must remain immutable.
