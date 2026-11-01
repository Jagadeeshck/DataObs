# Six-team execution and merge guide

All teams branch from latest main. Kiro agents are scoped by `docs/development/team-ownership.md`. Team 0 reviews shared paths and owns final merges and promotion.

**Recommended source merge order:**
1. Team 0 **only if** shared infrastructure blocks domain work (versions, migrations, CI, API packaging, Kind, recoverability). Otherwise skip to 2.
2. Team 5 shared Console quality and browser harness (unblocks Team 1/2 Console workflows).
3. Team 2 Data Product and quality→incident E2E; involve Team 3 for incident contract.
4. Team 1 Kafka/Pathway domain fixes after shared browser/migration fixes.
5. Team 3 incident and Team 4 provider changes **only if** current mandatory tests find real defects; otherwise submit evidence without code churn.
6. Team 0 final merge/freeze/certification **after all source PRs**. No source changes while candidate evidence is being evaluated; if changes occur, re-freeze and rerun all mandatory evidence.

### PR template (use in description)
- Base SHA, team, exact owned files, first failing error/run (or enhancement acceptance).
- Root cause; change made; non-goals; cross-team touches approved.
- Focused tests; real integration tests; browser/axe if applicable; skipped count.
- Producer workflow ID/SHA/attempt, retained artifacts and independent verification.
- Risk/rollback, supported scope impact, release-blocker state.

### Coordination
Team 0: unblock shared platform and maintain version/evidence truth.
Team 1: Kafka/Pathway and stream evidence.
Team 2: data quality, jobs, lineage, products, OTLP-to-incident E2E.
Team 3: incident/OCC/notifications/safe automation regression.
Team 4: SDK, packaged collection and honest provider support.
Team 5: Console quality/cross-browser/a11y plus integrated API UX.
