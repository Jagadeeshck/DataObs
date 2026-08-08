# Elastic Cases and Workflows threat model

The shared Kibana transport fixes the configured origin, rejects URL credentials and redirects, validates space/resource path segments, verifies TLS, bounds timeouts and response bytes, and emits bounded error codes. Credentials exist only in server secret configuration. Browser-controlled hosts, paths, spaces, Case owners, connector IDs, Workflow IDs and YAML are not accepted.

Reservations and exact deterministic references mitigate duplicate creation and Case-adoption attacks. Safe Remediation supplies actor binding, idempotency and execution fences. Workflow linting denies network/script escape hatches and external connector pushes. Cross-tenant, cross-environment and cross-space access fails closed. Bounded free text must pass the existing secret validator.
