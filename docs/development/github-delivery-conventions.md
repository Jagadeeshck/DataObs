# GitHub delivery conventions

## Labels

Team: `team:platform`, `team:streams`, `team:quality-jobs`, `team:incidents`, `team:integrations`, `team:console`.
Capability: `capability:backend`, `capability:api`, `capability:console`, `capability:integration`, `capability:security`, `capability:deployment`, `capability:certification`.
Release: `release:beta-1`, `release:post-beta`.
Status: `status:contract`, `status:implementation`, `status:integration`, `status:certification`, `status:blocked`.

Recommended Project fields: **Team, Product pillar, Release, Priority, Status, Dependency, Contract status, Implementation status, Certification status, Risk**. Repository files do not create organisation teams.

## Branches and PRs

Use `codex/<capability-name>`; team labels belong in metadata, not branch names. Branch from current `main`, keep branches short lived, and rebase before integration. Do not create team integration branches. Gate incomplete user-facing work behind feature flags. Shared contracts require a separate contract PR before consumer changes.
