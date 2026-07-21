# Open issue triage

Recommendations only; no GitHub issue was mutated. Human owners must review and apply changes.

| Issue | Original premise | Current repository reality | Capability IDs | Recommendation | Replacement roadmap item | Evidence | Required human action |
|---|---|---|---|---|---|---|---|
| #24 | Four-tower product framing | Canonical architecture has six pillars | `platform.architecture` | supersede | Phase A truth | six-pillar architecture and ledger | Close with replacement link |
| #25 | Grafana-first experience | Console exists; Kibana/Elasticsearch are authoritative | `console.command`, `integration.optional` | move_optional | Phase B Console certification | React routes; Alloy integration | Rewrite as optional export |
| #28 | Equal OpenSearch backend | Elasticsearch is authoritative | `integration.elastic`, `integration.optional` | move_optional | Phase A truth | Elastic manifest and integration docs | Remove equal-plane acceptance criteria |
| #29 | Asset catalog aspiration | Asset APIs and UI foundation exist | `data.asset360` | rewrite | Phase C Asset/Pathway | API and React files | Scope remaining workflow/evidence |
| #30 | Lineage/pathways aspiration | Pathway foundation exists | `data.pathways` | rewrite | Phase C Asset/Pathway | pathway worker and UI route | Replace title-level completion claims |
| #31 | PostgreSQL foundation | Principal scanner workflow exists but is unvalidated | `data.postgres` | rewrite | Phase B certification | scanner code and defined integration test | Require retained real-stack evidence |
| #32 | Autonomous remediation | Autonomous remediation is excluded | `incidents.workbench` | close_not_planned | Phase D controlled workbench | approvals/action foundations | Close or rewrite to approved actions |
| #46 | Kafka monitoring | Observer/inventory is functional unvalidated | `streams.kafka` | split | Phase B and Phase C Stream 360 | observer and Console route | Split certification from UI completion |
| #47 | Stream provider model | Provider-neutral foundation exists | `streams.connect_schema` | keep | Phase C Stream 360 | streaming package | Add explicit evidence gates |
| #48 | Stream detail completion | Detail routes exist without full browser proof | `streams.detail` | rewrite | Phase C Stream 360 | API/routes | Require browser/accessibility proof |
| #49 | Durable updates/actions | Foundation exists, safety evidence incomplete | `streams.live_actions` | split | Phase C Stream 360 | stream routes | Separate SSE durability and actions |
| #50 | Incident automation completion | Core is functional unvalidated; workbench incomplete | `incidents.core`, `incidents.workbench` | split | Phase D workbench | incident services/domain | Split lifecycle from workbench |
| #51 | Production readiness | Product readiness remains blocked | `platform.deployment`, `platform.iam`, `platform.backup_restore` | rewrite | Phase E hardening | production audit | Replace blanket claim with evidence gates |
