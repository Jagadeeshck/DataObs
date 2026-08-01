# Administration Console data handling

The UI may render safe subjects, opaque binding IDs, roles, trusted scopes, revisions, timestamps, actors, safe request IDs, and configuration categories supplied by supported contracts. It never renders tokens, raw claims/JWTs, cookies, JWKS material, credentials, raw headers/errors, Elasticsearch endpoints, environment dumps, or unrelated storage internals.

Telemetry contains stable route/mutation/result/recovery categories only; subject, binding, tenant, and environment IDs are prohibited. Local storage key `dataobs.console.preferences.v1` contains only validated density, time-zone display, and motion choices. It contains no identity, scope, permission, role binding, form, response, or secret data.
