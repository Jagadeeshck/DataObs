# DataObs incident automation

> Elastic Cases and reviewed Elastic Workflows extend this control plane without replacing it. See [Incident, Case and Workflow orchestration](incident-case-workflow-orchestration.md).

This document describes the Elastic Streams and Workflows incident-automation vertical slice. Findings are normalized into versioned contracts, deterministically deduplicated and correlated into incidents, then linked to Kibana Workflows, Elastic Cases, notifications, approval records and safe DataObs actions.

Technical-preview boundaries: Observability Streams enrichment and event-driven workflow triggers are optional. Critical detection, incident persistence, deduplication, notifications and recovery use stable DataObs and documented Elastic/Kibana APIs. No autonomous or destructive remediation is enabled; safe actions cannot alter PostgreSQL schema, mutate business data, execute arbitrary SQL/shell, change credentials, disable constraints or kill arbitrary sessions.

Least-privilege API keys should be scoped separately for workflow management, workflow execution, execution read, Cases, alert rules and optional read-only Streams access. Approval and action APIs enforce tenant isolation, idempotency, bounded retries and audit records.
