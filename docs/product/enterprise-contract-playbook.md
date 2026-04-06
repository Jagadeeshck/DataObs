# DataObs Enterprise Contract Playbook

This playbook turns market expectations into concrete DataObs implementation priorities so you can win project-based contracts with large enterprises.

## Competitive references reviewed

- Monte Carlo Data: https://www.montecarlodata.com
- Bigeye: https://www.bigeye.com
- Acceldata ADM Platform: https://www.acceldata.io/platform

## What buyers expect during enterprise evaluations

1. **Fast, clear reliability outcomes**
   - Reliability scoring and SLA tracking
   - Tiered incident severity and ownership
2. **Root-cause acceleration**
   - Column-level lineage and blast-radius context
   - Suggested next actions and runbook links
3. **Governed automation**
   - Policy-aware actions with auditable approvals
   - RBAC around sensitive datasets and remediation workflows
4. **Business-level accountability**
   - KPI impact framing for every incident
   - Cost and pipeline efficiency visibility for FinOps stakeholders

## DataObs implementation priorities (now encoded in code)

The new `enterprise_backlog` capability engine (`src/core/enterprise_blueprint.py`) prioritizes high-value roadmap investments for contract pursuits.

### Priority order

1. **Data Product SLOs and Reliability Scorecards**
2. **No-Code Monitor Bootstrap Templates**
3. **Lineage-Aware Incident Triage Workbench**
4. **Policy-Aware AI and Access Guardrails**
5. **Pipeline Cost and FinOps Visibility**

## How to use in sales + delivery motions

### 1) During discovery
- Ask the client which capabilities they already have.
- Call `GET /strategy/enterprise-backlog?implemented=<csv_keys>`.
- Share the top 2 recommendations as the first sprint scope.

### 2) During proposal drafting
- Convert each recommended capability into a work package:
  - design + integration
  - rollout + runbook
  - executive scorecard
- Tie each package to measurable outcomes (MTTR reduction, SLA attainment, issue prevention rate).

### 3) During pilot execution
- Deploy monitor bootstrap templates first to show quick wins.
- Add lineage-aware triage enrichment to incident payloads.
- Present monthly SLO scorecards with reliability trend and error budget usage.

## Suggested proposal structure for large contracts

1. **Current-State Assessment (2-3 weeks)**
2. **Reliability Baseline & SLO Design (3-4 weeks)**
3. **Automated Detection + Incident Workflow (4-6 weeks)**
4. **Governance, AI Guardrails, and FinOps Integration (4-6 weeks)**
5. **Enablement, Runbooks, and Managed Operations Handover (2-3 weeks)**

This structure helps procurement teams see implementation confidence, governance coverage, and business outcomes early.
