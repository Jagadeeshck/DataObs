# Console navigation and context safety

The Console trusts tenant membership, environments, permissions, and capability
status only from `/api/v1/auth/me`. Permission filtering improves UX but never
replaces backend tenant/RBAC enforcement. Permissions are held in React memory
and are not persisted in local or long-lived browser storage.

Tenant/environment switches validate membership, update only allowlisted query
keys, advance the refresh generation, and cause abortable consumers to discard
prior-context responses. Entity links encode one bounded identifier segment and
reject controls, empty IDs, and unknown entity types. Access tokens, credentials,
webhooks, raw configuration, and sensitive evidence are prohibited from URLs,
history state, preferences, screenshots, and evidence artifacts.

An absent/unreachable capability status is unknown or unavailable, never
healthy. Unauthorised deep links recover through `/unauthorised`; hidden but
routable entries still depend on backend enforcement. Route errors are
contained without clearing trusted identity or revealing backend/import errors.
