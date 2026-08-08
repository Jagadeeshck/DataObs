# Elastic Cases integration

DataObs incidents remain authoritative for lifecycle, severity, ownership, approvals and recovery. An Elastic Observability Case (`owner=observability`, connector `.none`) is an external collaboration projection only. The deterministic `dataobs-ref-<hash>` tag and a tenant/environment/incident/space reservation enforce at most one managed active Case. An uncertain create becomes `create_reconciliation_required`; it is never blindly retried. Closing a Case never closes an incident, and resolving an incident never automatically closes its Case.

Environment-to-space selection is server configuration. Reads verify the owner and exact deterministic tag before adopting remote state. Titles, descriptions, tags, comments and assignees are bounded; provider responses are explicitly adapted rather than persisted wholesale.
