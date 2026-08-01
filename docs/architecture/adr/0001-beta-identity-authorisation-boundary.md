# ADR 0001: Beta identity and authorisation boundary

- Status: Accepted
- Date: 2026-08-01

OIDC is the production identity authority and Elasticsearch is the durable authorization-policy and append-only audit store. Bindings scope a user, group, or explicit service principal to one tenant and listed environments. Route-template authorization is method-aware and deny-by-default.

Production uses `bindings` or `intersection`; `claims` is limited to development, test, and PoC. A configured trusted OIDC group may bootstrap a platform administrator while bootstrap is enabled. Bootstrap use and all IAM mutations are audited, and the final durable administrator cannot be disabled. Services are identified by validated `azp`/`client_id`, must be allowlisted, and require a `service` binding; interactive group roles never flow to them.

Tenant and environment selectors are untrusted input validated after identity and binding resolution. Missing identity, policy, key, IAM store, or audit store fails closed. Mutation audit failure fails the mutation. Authentication-denial audit failures return a sanitized denial. Rollback can stop writers and disable bootstrap, but cannot delete released migration resources or append-only evidence.
