# DataObs Kiro workspace pack

This pack is **repository scoped**: use its `.kiro/` inside the root of `Jagadeeshck/DataObs`. Do **not** copy it to `~/.kiro/` or another workspace. `docs/kiro/` contains human-readable planning documentation.

## Reviewed baseline (2026-11-01)
- GitHub `main` observed at `60de7cb58a3357f2fc6cd624c23ed381de1517d7` (commit text announces Elastic Stack 9.5.5 and DataObs 1.0.0).
- `RELEASE.md` and Console package describe `1.0.0`, but `docs/release/current-production-readiness.md` still describes `0.2.0`, **NO_GO**, zero supported platforms, and a prior commit. README also says the repo is not production released.
- The GitHub Release workflow failed on the observed head; many other workflows failed. Never infer a certified release from a version bump or commit title.
- First-release target: **Friday 2026-11-06**, conditional on exact-SHA evidence, supported-platform, security, backup/restore, browser and supply-chain approval.

## Kiro layout
- `.kiro/steering`: always-on product/technology/structure/safety plus context-specific release and domain guidance.
- `.kiro/agents`: six scoped team agents and a release coordinator. Agents explicitly load project steering and skills.
- `.kiro/skills/*/SKILL.md`: specialized step-by-step skills.
- `.kiro/workflows`: manually invoked release / implementation / triage recipes.
- `.kiro/specs/first-release-week`: spec-driven requirements, design and tasks for this week's release.
- `docs/kiro`: product vision, phased roadmap and team merge order.

## Quick start
1. Open the DataObs repository and inspect this configuration PR; no existing `.kiro` was present when audited.
2. Open **only DataObs** as a Kiro workspace; use workspace steering, not global steering.
3. Select a Team 0–5 agent or `release-coordinator`; load the first-release spec. Agents do not have auto-approved destructive shell permissions.
4. Start with `/release-readiness` workflow; establish the current exact SHA and failures before writing code.
5. Use `/implement-owned-change` for domain work and `/certify-release` only after the final merge.
6. Update the spec task checkboxes from evidence, not from expectations.

Kiro syntax reference: https://kiro.dev/docs/steering/ , https://kiro.dev/docs/custom-agents/ , https://kiro.dev/docs/custom-agents/configuration-reference/ .
