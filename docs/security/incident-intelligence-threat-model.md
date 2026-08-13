# Incident intelligence threat model

The primary risks are cross-tenant/environment disclosure, ID enumeration, candidate injection, weight or DSL manipulation, unbounded/high-cardinality queries, cursor tampering, relationship spoofing, unauthorized decisions, unsafe text, and secret-bearing logs.

Server-owned scoring and candidate DSL, immutable scope predicates, allowlisted bounds, deterministic scope-bound identities, incident-read authorization, incident-write authorization for decisions, OCC, and safe categorical features are required controls. Credentials, tokens, raw SQL/logs/stacks, PII, workflow payloads, and comment bodies are prohibited features.
