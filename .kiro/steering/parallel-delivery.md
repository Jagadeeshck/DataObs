---
inclusion: always
---
# Parallel team delivery

DataObs work runs as six concurrent teams plus a release coordinator. These rules
keep parallel work collision-free. They complement `structure.md` (ownership map)
and never override `safety-and-evidence.md`.

## Each team stays in its lane
- A team edits only files it owns per `structure.md` / `docs/development/team-ownership.md`.
- Touching a shared contract (`src/api/`, `packages/domain_model/`, generated
  schema/OpenAPI, `ui/dataobs-console/src/api/`, root config, capability ledger,
  `.github/workflows/`) requires the owning domain + Team 0 — flag it, do not edit
  silently in a parallel branch.

## Branch and PR discipline
- Every team works on its own short-lived branch off the latest `main`:
  `team-<n>/<short-topic>` (e.g. `team-1/kafka-lag-evidence`).
- One root cause → one focused PR. Never push to `main`.
- Never force-push a shared branch or rebase another team's branch.

## Merge order (coordinator-owned)
1. Team 0 shared platform/infra fixes first (if blocking).
2. Team 5 Console shell/shared components before dependent domain browser checks.
3. Team 2, Team 1 domain changes.
4. Team 3 / Team 4 only when a mandatory defect exists.
5. Team 0 release certification last, on the frozen SHA.

Each merge invalidates prior SHA-based evidence. Re-run mandatory gates on the new SHA.

## Conflict avoidance
- If two teams need the same shared file, the coordinator sequences them; the second
  rebases on the first's merged result. Teams do not both edit it in parallel.
- Migrations: only Team 0 adds migrations; IDs are strictly increasing and additive.
  Next free ID is the current terminal + 1. Never edit a released migration.

## Handoff contract (every team PR records)
- Team owner and exact files changed.
- Root cause / contract implemented.
- Tests run and result; evidence artifact / run IDs; "no mandatory skips" statement.
- Shared-path impact and which team must review.
- Dependencies and required merge order.

## Working in a workflow run
- Teams share ONE repo working tree. In a parallel run you MUST isolate with a private
  git worktree — never `git checkout` in the shared tree (a concurrent checkout clobbers
  your uncommitted work):
  `git worktree add -b team-<n>/<topic> /tmp/dataobs-team-<n> <base-sha>` then `cd` there.
- Use a uniquely-named branch; do not reuse a generic name another team might also pick.
- Do the owned slice, commit to the team branch, and report via the step summary. Do not
  merge, publish, or start another team's work.
- Signal `success` only when the slice's exit criteria are met and verified.
