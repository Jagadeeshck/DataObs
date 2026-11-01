---
name: incident-safety
description: Develop incidents, notifications and human-approved response safely with deduplication and durable audit.
---
# Incident Safety

1. Inspect Team 3 incident lifecycle/OCC and authorization contracts.
2. Ensure deterministic correlation, dedup, actor attribution, audit, replay and scope isolation.
3. Mock Slack/PagerDuty/ServiceNow; do not send real on-call notifications from certification.
4. Failed/unknown external response must not be blindly retried; persist redacted outcome.
5. Human approval, fencing, separation of duties and deny-by-default remediation remain mandatory.
6. Run incident Workbench, security, notification and Quality→incident E2E proofs.
**Output:** safe action matrix, tests and evidence with no unauthorized side effects.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
