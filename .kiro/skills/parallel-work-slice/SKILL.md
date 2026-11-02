---
name: parallel-work-slice
description: Execute one owned team work slice efficiently in a parallel delivery run — branch, minimal change, smallest proving tests, focused PR, handoff. Use when a DataObs team agent is given a single scoped task to deliver without merging.
---
# Parallel work slice

A tight, credit-efficient procedure for delivering one owned slice. Obey
`safety-and-evidence.md`, `parallel-delivery.md`, and `credit-efficiency.md`.

## 1. Confirm scope (no exploration sprawl)
- Restate: owner team, exact owned files/paths, exit criteria.
- If the brief names the files, go straight to them. Do not scan the whole repo.
- If you must explore, delegate ONE context-gatherer pass; treat its output as your reads.

## 2. Isolated worktree + branch (REQUIRED for parallel runs)
- All teams share one repo. **Never `git checkout` in the shared working tree** during a
  parallel run — a concurrent team's checkout will clobber your uncommitted work.
- Create a private worktree and branch in one step:
  `git worktree add -b team-<n>/<short-topic> /tmp/dataobs-team-<n> <base-sha>`
- `cd /tmp/dataobs-team-<n>` and do all work there. Never work on `main`.
- When done and committed, the branch is visible in the shared repo automatically; leave
  the worktree for the coordinator to remove, or `git worktree remove` it yourself.

## 3. Implement the minimal change
- Edit only owned files. Use `str_replace` with small anchors.
- A shared-contract touch (`src/api`, `packages/domain_model`, generated schema,
  `ui/.../src/api`, root config, ledger, CI, migrations) → flag for Team 0, do not
  silently edit. Only Team 0 adds migrations (additive, next free ID).
- Preserve the domain's honesty semantics (missing vs zero, stale vs current,
  unknown vs error). No unsupported claims.

## 4. Verify proportionally
- Run the smallest test set that proves the slice first.
- Backend: `ruff check <paths> && black --check <paths> && pytest <targeted> -q`.
- Console: `pnpm typecheck && pnpm lint && pnpm test` (add Playwright/axe only if the
  slice touches browser surfaces).
- Do not re-run gates that already passed with no further change.

## 5. One focused PR
- One root cause → one PR. Small diff. Commit to the team branch; do not merge.

## 6. Handoff contract (report this, keep it compact)
- Owner team and exact files changed.
- Root cause / contract implemented.
- Tests run + result; evidence/artifact or run IDs; "no mandatory skips" statement.
- Shared-path impact and which team must review.
- Dependencies and required merge order.

## Stop conditions
- Exit criteria met and verified → signal success with the handoff summary.
- Blocked (missing dependency, shared file owned by another team, failing gate you
  cannot fix in-lane) → stop and report the blocker. Do not speculate or expand scope.
