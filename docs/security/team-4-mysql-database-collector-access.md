# MySQL collector least-privilege access

Grant only connection and catalog visibility needed for approved schemas. Grant `SELECT` on a business relation only when its aggregate freshness or profiling policy is explicitly enabled. Never grant administration, DDL, mutation, `FILE`, `SUPER`, `SYSTEM_USER`, `PROCESS`, `RELOAD`, replication, or local-infile privileges.

Production requires a trusted CA plus certificate and hostname verification (`ssl_disabled=False`, `ssl_verify_cert=True`, `ssl_verify_identity=True`). Only shared `env:`, file, and Kubernetes file secret references are accepted; inline passwords and credential-bearing URLs are rejected. Resolved credentials are connection-only and are never observations, errors, or checkpoints.

Fixed provider statements and the shared mutation guard reject mutations and administration, including `LOAD DATA LOCAL INFILE`. Metadata SQL selects no business rows. Explicit freshness/profiling reads are aggregate-only. MariaDB connections fail closed with `server_product_mismatch`.
