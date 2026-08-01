# OpenLineage ingestion security

Collectors require `collection:ingest`; job and run browsing requires `jobs:read`. Authentication selects an already-authorized tenant and environment, and request bodies cannot override either. Service identities intended for collection must not receive interactive Console roles.

Requests are size and shape bounded. Credential, authorization, token, secret, connection string, SQL/query, environment, and stack-trace keys are redacted recursively. Raw requests, bearer tokens, SQL, exception bodies, and records are not stored.
