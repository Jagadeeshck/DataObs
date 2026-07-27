# Evidence-gated product roadmap

No delivery dates are implied. The capability ledger, not issue or PR titles, determines current state.

## Phase A — Stabilization and truth

### Migration/OCC/replay corrections, capability ledger, and CI enforcement
- **Current state:** corrections are functional but unvalidated; the truth tooling is implemented in this milestone.
- **Entry criteria:** released migrations `0001`–`0019` remain checksum-identical.
- **Deliverables:** authoritative ledger, deterministic docs, documentation truth gate.
- **Evidence gate:** validators, focused tests, links, and generated-drift checks pass in retained hosted CI.
- **Exit criteria:** reports and artifacts are retained and review links resolve.
- **Dependencies:** the audited implementation baseline through PR #168 and repository CI.
- **Non-goals:** product features or migration edits.

## Phase B — Unified real-stack certification

### Elasticsearch/Kibana 9.4.2, PostgreSQL, Kafka, OpenLineage, and Console certification
- **Current state:** components range from foundation to functional unvalidated.
- **Entry criteria:** Phase A exits and a reproducible version-pinned environment exists.
- **Deliverables:** unified stack, Console journey, browser/accessibility/security scenarios.
- **Evidence gate:** retained real-stack and hosted CI artifacts for all named components.
- **Exit criteria:** applicable browser, accessibility, security, and upgrade dimensions pass.
- **Dependencies:** Elasticsearch/Kibana 9.4.2 and test data services.
- **Non-goals:** additional providers or messaging systems.

## Phase C — Complete the existing core product

### Monitoring, Data Products/RCA, Job/Run Explorer, Asset/Pathway, and Stream 360
- **Current state:** runtime and Console foundations exist; final-head hosted certification remains incomplete.
- **Entry criteria:** Phase B baseline is reproducible.
- **Deliverables:** complete existing workflows and coherent Console navigation.
- **Evidence gate:** focused integration plus browser/accessibility and security evidence.
- **Exit criteria:** each capability independently meets its ledger next gate.
- **Dependencies:** collection, storage, APIs, and Console certification.
- **Non-goals:** differentiating future pillars.

## Phase D — Incident and Automation Workbench

### Collaboration, Cases, Workflows, approvals, actions, verification, and learning
- **Current state:** domain/storage/service foundations exist; Console and execution remain incomplete.
- **Entry criteria:** incident correctness and IAM safety prerequisites have retained evidence.
- **Deliverables:** controlled workbench workflows, notifications, reviews, and analytics.
- **Evidence gate:** lifecycle, concurrency, approval, security, recovery, and browser tests.
- **Exit criteria:** bounded, auditable workflows pass failure and recovery scenarios.
- **Dependencies:** IAM/RBAC design, incident repository, action safety.
- **Non-goals:** autonomous remediation.

## Phase E — Enterprise hardening

### OIDC/RBAC, HA, backup/restore, deployment, release, and product SLOs
- **Current state:** IAM and backup/restore are not started; packaging is foundational.
- **Entry criteria:** core workflows are stable and threat models are current.
- **Deliverables:** identity enforcement, HA, recovery, supported deployment and release controls.
- **Evidence gate:** security, scale, restore, upgrade, HA, and release rehearsals retained.
- **Exit criteria:** production-candidate criteria are explicitly reviewed; no readiness is implied early.
- **Dependencies:** operator ownership, environments, licensing and support model.
- **Non-goals:** new product pillars.

## Phase F — Differentiating pillars

### FinOps, Business Reliability, AI/Agent Observability, Advisor, and providers
- **Current state:** FinOps, scorecards, AI/Agent Observability, Advisor, Snowflake/cloud connectors, and multi-cloud lineage are not started.
- **Entry criteria:** Phase E evidence gates pass and customer demand is documented.
- **Deliverables:** in order: FinOps; Business Reliability Scorecards; AI/Agent Observability; Advisor; Snowflake/cloud providers; multi-cloud lineage; then demand-led messaging systems.
- **Evidence gate:** capability-specific executable, hosted, security, scale, and user-workflow evidence.
- **Exit criteria:** each new capability independently satisfies promotion policy.
- **Dependencies:** provider agreements, licensing, customer validation, hardened platform.
- **Non-goals:** speculative connectors or delivery dates.

## Phase B — unified certification environment

Phase B consolidates the existing Elastic, PostgreSQL, Kafka, OpenLineage-fixture, API, incident, browser, and security validation paths. Exit remains evidence-gated: a green hosted summary, retained redacted artifacts, and individual human-reviewed ledger decisions are required. Fixture contracts do not certify real Airflow, dbt Cloud, or Spark providers, and whole-product readiness remains blocked.
