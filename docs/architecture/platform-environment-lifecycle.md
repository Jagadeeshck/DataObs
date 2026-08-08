# Platform environment lifecycle

Environment states are `requested → provisioning → configured → validating → ready`; explicit degraded, maintenance, upgrade, rollback, retiring, retired and failed paths are encoded in `src/platform_lifecycle/service.py`. Cluster, installation, tenant, deployment-plan and failover states are separate.

Every mutation requires authenticated explicit permission, bounded reason code, actor from validated identity, idempotency key, `If-Match` OCC revision, timestamp and append-only evidence. Repeating the completed target is idempotent; arbitrary state assignment is rejected.

Desired state validates against `config/platform/environments.schema.json` and hashes canonical sorted JSON. Approved plans are immutable; desired-state changes create a new plan. Plans contain declarative differences and verification/rollback metadata, never shell, kubectl or Terraform commands.

Maintenance supports read-only, ingestion pause, worker pause and tenant suspension without bypassing authentication or authorization. It requires expiry when temporary, reason, permission, OCC and verification.
