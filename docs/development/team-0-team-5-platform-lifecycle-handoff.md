# Team 0 → Team 5 platform lifecycle UI handoff

Build inventory views for environments, clusters, fleet, tenants, plans, promotions, drift, capacity, upgrade/rollback and offboarding against `/api/v1/platform/*`; do not synthesize state client-side. Use cursor pagination when introduced, retain request ID, and send `Idempotency-Key` and `If-Match` for mutations. A 412 reloads the record; it never silently overwrites.

Render all documented states and approvals. `unknown`, `unvalidated`, hosted `pending`, and `functional_simulation` need distinct non-green presentation. Empty, loading, permission-denied, conflict, validation, unavailable and partial-evidence states need separate UI. Display safe references and fingerprints only; redact tokens, credentials, kubeconfig, secret values, raw Helm values and tenant data.

Permission gates are explicit (`environments:*`, `clusters:*`, `installations:*`, `tenants:provision|suspend|offboard`, `platform_promotions:execute`). UI hiding is not authorization. Destructive offboarding shows preview, retention/backup blockers, independent approval, verification and append-only evidence. It must never offer arbitrary namespace, release name, resource name, kubectl, Terraform target or shell input.
