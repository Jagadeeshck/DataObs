# Kafka DSM threat model

Credentials use secret references, logs/config diffs redact secret-like settings, raw payload collection has no endpoint, and message keys are dropped or hashed. Tenant/environment are mandatory identity dimensions. Read-only ACLs and scoped API principals limit blast radius. Cloud auth adapters, destructive remediation, and unrestricted inspection are out of scope.
