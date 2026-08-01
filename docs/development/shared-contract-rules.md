# Shared contract rules

Team 0 approval is required for migrations; Elasticsearch mappings, aliases and data streams; shared IDs; tenant/environment contracts; authentication and permissions; the common evidence envelope; generated OpenAPI schema; shared Console transport; certification evidence; Helm foundations; and release manifests.

A feature PR must not silently redefine a shared contract. Cross-team delivery proceeds as: **1. Contract PR**, documenting compatibility and ownership; **2. consumer implementation PRs**; **3. integration PR**; **4. certification** with exact-commit hosted evidence. Additive compatibility is the default. Breaking changes require an ADR, rollout and rollback.
