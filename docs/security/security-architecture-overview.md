# Security architecture and posture overview

DataObs uses OIDC identities at the browser/API boundary, explicit RBAC route permissions, tenant/environment context, scoped service identities, Elasticsearch persistence, and secret-reference-only deployment contracts. Privileged and break-glass activity uses lifecycle approval and audit controls. Kubernetes deployment controls target PSS Restricted, immutable images, NetworkPolicy and least-privilege accounts. Release foundations produce SBOM, provenance and signatures, but tooling or workflow presence alone is not evidence that a particular candidate was generated, signed, hosted-tested, or independently verified.

Encryption in transit is required at external production boundaries. Elasticsearch/cloud disk encryption is a deployer/provider responsibility. DataObs v1 makes no application-level encryption-at-rest claim. Data minimization prohibits credential/token/private-key and database-business-row persistence; provider contracts govern conditional SQL/schema metadata.

The canonical inventories and evaluator use fail-closed evidence states. They do not constitute external certification, auditor approval, regulatory approval, or a penetration-test result.
