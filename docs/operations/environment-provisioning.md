# Environment Provisioning

## Preconditions
Authoritative inventory and current evidence are available; unknown mandatory evidence stops execution. External dependencies are reachable.

## Permissions and approval
Use the narrow lifecycle permission. Production, destructive, promotion, rollback and failover actions require the existing privileged approval contract and a change reference; requester cannot self-approve destruction.

## Plan and execution
Create desired state, register eligible cluster and installation, configure references, validate migrations/readiness, then transition ready.

Execution is declarative and idempotent with `Idempotency-Key`, `If-Match`, bounded reason code and validated actor. Operators use reviewed adapters; the API accepts no shell, kubectl or Terraform target.

## Verification
Verify readiness, authorization and tenant isolation, external Elasticsearch/migration status, telemetry, critical alerts, drift and append-only audit evidence. Preserve unknown/unvalidated honestly.

## Rollback
Stop and select the recorded rollback plan. Confirm migration compatibility and backup before application rollback. Do not reverse released migrations or delete recovery data.

## Evidence and escalation
Retain target SHA, plan ID, actor/approver, timestamps, checks, logs/traces, support profile and result. Escalate blocked security, backup, migration, data-integrity, SLO or external-provider checks to Team 0 and the dependency owner.

## Prohibited actions
No authorization bypass, secret output, mutable release tag, arbitrary names/commands, OpenSearch substitution, immediate tenant deletion, self-approval, or healthy/support/HA/DR claim without evidence.
