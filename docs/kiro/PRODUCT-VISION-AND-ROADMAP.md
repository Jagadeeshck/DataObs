# DataObs product vision & phased development plan

**Vision:** One Elasticsearch-native product for data platform and data product operators that correlates infrastructure, streams, jobs, quality, lineage, product trust, incidents and eventually financial/business impact and AI-assisted investigation.

## Differentiator
Instrument once through OTLP/OpenLineage + bounded native collectors. Normalize to tenant-scoped, versioned evidence in Elasticsearch. Let operators move from **signal → affected assets and dependencies → root-cause candidates with confidence → incident → verified response** in one DataObs Console. Support enterprise multi-tenancy, audit and explainability from day one.

## Product pillars and phases
| Pillar | First bounded release | Next (1–2 iterations) | Later |
|---|---|---|---|
| Platform | API/Console/monitoring foundation, health, secure packaging | HA, fleet/capacity operational visibility | advanced governance, platform economics |
| Data Pipeline | Kafka Stream 360/Pathways, Jobs/Run 360, OTel/OpenLineage contracts where certified | end-to-end service/pathway SLOs and dependency impact | cross-platform predictive saturation |
| Data | Monitor checks, findings, lineage and Data Products where certified | trust scores, quality SLOs, richer data products | broad semantic anomaly intelligence |
| FinOps/Cost | Domain architecture and data contracts only | observed cost attribution and unit economics | optimization and forecasting |
| Business | Business context model only | business journey impact and customer-facing SLIs | richer revenue/regulatory impact |
| AI/Agent | Human-controlled, explainable recommendations only | assisted triage over cited evidence | reviewed agent workflows, never unrestricted execution |

## Design principles
- Open standards and Elasticsearch core, but no universal provider promises.
- Six pillars are strategic **vision**, not a first-release feature checklist.
- Visible product journeys must have working API, tenant boundary, semantics, SLO/error states, tests and evidence.
- OpenTelemetry trace/resource correlation + OpenLineage graph should connect data quality, pipelines, infrastructure and incidents.
- Use one shared domain/evidence model and one navigation architecture; no duplicated collector or incident subsystem.
- Explainability: show source timestamps, freshness, coverage, confidence and missingness.
- Keep cost and AI claims disabled/roadmap until genuinely implemented and certified.

## Product backlog hierarchy
P0 first release: installation, migration, auth, tenant isolation, source-of-truth version, recovery, primary investigation path, evidence-gated Console.
P1 beta hardening: multi-tenant HA, production-scale proof, better supported connector coverage, SLO evaluation and cost attribution foundation.
P2 differentiation: business context, reliability/finops relationships, assisted incident reasoning with citations, human approvals.

## Source-of-truth rule
The roadmap proposes intent; `docs/product/capability-ledger.yaml`, latest evidence and current code govern actual implementation status. Never promote a capability from `functional_unvalidated` solely because its files exist.
