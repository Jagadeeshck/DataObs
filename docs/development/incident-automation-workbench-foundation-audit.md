# Incident and Automation Workbench foundation audit

Baseline: `45867e3` (merge of PR #101). Migrations `0001` through `0010` were present; this change does not modify their declarations. PR #101 completed Stream 360, but its merge commit contains no hosted workflow-run evidence.

| Capability | Current implementation | Blocking gap | Required action | Test evidence |
|---|---|---|---|---|
| Incident persistence | Test-oriented process-local repository | Production wiring is not durable | Inject the fixed-alias Elasticsearch repository; fail startup without it | repository contract tests pending real stack |
| Finding ingestion | deterministic normalization exists | source authentication, DLQ and batch API incomplete | add source-bound routes and durable event writes | deterministic unit tests |
| Correlation | keys and basic scoring exist | explanations, budgets, merge/split and recurrence incomplete | persist versioned feature decisions and audited reassignment | pending |
| Lifecycle | transitions previously unconstrained | scope enforcement remains at API layer | legal graph and required reasons added | lifecycle unit tests |
| Actions | placeholder could claim execution | adapters and durable audit incomplete | placeholder removed; require allowlisted adapter | safety unit tests |
| Approvals | decision could create missing request | Elasticsearch repository and notifications incomplete | require durable request, expiry and separation of duties | policy unit tests |
| Timeline/collaboration | event list and collaboration projections incomplete | comments, watchers and tasks need durable APIs | append-only events and OCC projections | pending |
| Elastic Cases | identifiers only | synchronization and reconciliation incomplete | public API client with space allowlist | real-stack pending |
| Elastic Workflows | YAML validator/deployer baseline | public API capability validation incomplete | honest capability state and execution reconciliation | validator tests |
| Console | incident pages contain incomplete/static states | Inbox, workbench, approvals and automation journey incomplete | implement generated-contract screens | pending |
| Post-incident learning | absent | durable review and metrics absent | evidence-backed human-reviewed draft | pending |
| Real-stack assurance | no PR #101 hosted run | Playwright, axe and security stack evidence absent | run pinned stack gates before removing draft | pending |

A model, enum, validator, placeholder response, or static page is not counted as executable capability. This milestone remains incomplete and is not production-ready.
