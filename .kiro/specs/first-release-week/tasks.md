# Implementation tasks — release week

Check boxes only after exact-commit evidence. Parentheses indicate owner and merge dependency.

- [ ] T0-01: Review current SHA and release failures; reconcile app/chart/Console/Python/Elastic 9.5.5 vs stale 0.2.0/9.4.2 claims. (Team 0; first)
- [ ] T0-02: Fix current shared CI, migrations, API packaging, Kind/Helm, MVP and recovery failures; verify real infra. (Team 0; before domain merges if blocking)
- [ ] T5-01: Fix shared Console static, browser and axe failures, without production fixtures. (Team 5; before Team 1/2 Console evidence)
- [ ] T2-01: Certify Quality, Data Products, Jobs/Run and Lineage plus real Quality→OTLP→ES→incident E2E. (Team 2; after T0/T5 prerequisites)
- [ ] T1-01: Certify Kafka, Streams and Pathways with real-stack, replay and tenant evidence; close owned regressions. (Team 1; after T0/T5 prerequisites)
- [ ] T3-01: Verify incident/OCC/notification safe outcomes and Team 2 integration; PR only for fresh defect. (Team 3; before final E2E evidence)
- [ ] T4-01: Verify SDK, packaged runtime and truthful supported provider matrix; PR only for fresh defect. (Team 4; before freeze)
- [ ] T0-03: Merge verified owned PRs in dependency order; rerun complete mandatory Gate 0 on final SHA. (Team 0)
- [ ] T0-04: Freeze exact candidate only after Gate 0 green; dispatch canonical Team 1–5 release workflows. (Team 0)
- [ ] T0-05: Independently verify supported platform, auth/tenant isolation, destructive restore, browser/a11y, real E2E, SBOM, provenance, signatures and digest-addressed install. (Team 0)
- [ ] T0-06: Publish v1.0.0 **only** if the actual version/scope is approved and protected authority returns GO; otherwise issue factual NO_GO + blocker report. (Team 0)

## Delivery order
Shared infra Team 0 (if required) → Console Team 5 → Data/Quality Team 2 → Streams Team 1 → conditional Team 3/4 → Team 0 final certification. Teams may diagnose in parallel; merges follow dependencies. After freezing, any source change restarts certification.
