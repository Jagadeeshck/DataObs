# ADR 0001: Beta identity and authorisation boundary

* Status: **Accepted**
* Date: 2026-08-01

OIDC is the production identity authority. Elasticsearch, through only migration-0020 aliases, is the durable authorization-policy and append-only security-event store. Bindings attach a user, trusted group, or explicit service client to roles within one tenant and optionally bounded environments. Route authorization is an exact method/template lookup and denies by default.

Production uses `bindings` or `intersection`; `claims` alone is restricted to development, test, and POC. Intersection additionally constrains binding access with trusted token tenant/environment claims. The tenant/environment selector is untrusted request input and is validated only after identity and bindings resolve. Unknown roles and disabled bindings grant nothing.

Configured trusted OIDC groups may bootstrap a platform administrator when bootstrap is enabled; no account or password is created. Bootstrap use and every binding mutation are audited. Services are identified by validated `client_id`/`azp`, must be allowlisted, and require `service` bindings; they do not inherit browser groups.

Authentication, permission denial, escalation, final-administrator protection, configuration rejection and mutation events are append-only and redaction safe. IAM mutation fails if its audit append fails. Failure to validate identity, retrieve authoritative bindings, resolve an exact policy, or access required production stores fails closed. The final active platform administrator cannot be disabled using a concurrency-unsafe read/write sequence.

Rollback stops IAM writers and disables bootstrap but retains bindings and security events. Released migration resources and append-only evidence are not rolled back or deleted.
