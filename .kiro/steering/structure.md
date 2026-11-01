---
inclusion: always
---
# Repository map and change ownership

Reference source of truth: `docs/development/team-ownership.md`.

- **Team 0:** `packages/elastic_store/`, `src/security/`, `src/config/`, `deploy/`, `helm/`, `.github/workflows/`, `scripts/certification/`, `scripts/release/`, `docs/release/`; shared platform/security/release.
- **Team 1:** Kafka observer, pathway worker, pathways package, stream/pathway API and Console features, stream tests.
- **Team 2:** quality/monitor/job/run/lineage/Data Product domain, relevant integrations and Console areas.
- **Team 3:** incident management, correlation, notifications, approval-bound automation, incident Console.
- **Team 4:** provider SDK/collection manager/scanners/integrations other than Team 1 Kafka and Team 2 Airflow/dbt/Spark.
- **Team 5:** Console shell, navigation, auth presentation, shared components, browser harness and accessibility.

Shared contracts in `src/api/`, `packages/domain_model/`, generated schema/OpenAPI, `ui/dataobs-console/src/api/`, workflows, root configuration and capability ledger require affected domain owner + Team 0 review.

## Ownership workflow
1. State team owner and exact files before modifying.
2. Open a new short-lived branch from latest `main`.
3. Keep one root cause / one PR where possible.
4. Never push directly to `main`, overwrite other team changes or merge without current CI.
5. Record test evidence and release impact in the PR.
6. Merge shared infrastructure first if blocking; Console shell before dependent domain browser checks; domain changes next; Team 0 release certification last.
