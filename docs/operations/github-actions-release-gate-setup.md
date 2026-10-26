# GitHub Actions release-gate setup

GitHub Actions execution is now functioning and hosted workflows are producing real runs. The first execution exposed
shared CI bootstrap defects; local validation is not hosted CI evidence and the representative repaired canaries must
pass before CI is described as healthy.

As checked again on 2026-09-13, the public Actions API exposes 25 push workflows for main SHA `469030b6`: 4 passed
and 21 failed. Playwright executed in hosted CI and reported product findings; it is not unavailable or `not_run`.
This supplied checkout still has no configured Git remote and `gh auth status` has no authenticated host, so it cannot
push the repair or trigger exact-recovery-SHA canaries. Do not confuse that local limitation with absent hosted runs.

1. In **Settings → Actions → General**, allow Actions and permit the repository's required first-party actions.
2. In **Settings → Rules → Rulesets** (or **Branches → Branch protection rules**), create or edit the rule targeting
   `main`; require a pull request and require branches to be up to date before merging.
3. Run the bounded hosted canary set, beginning with **Team delivery foundation**. Select emitted checks rather than
   typing speculative names; make checks required only after their final stable names and behavior are confirmed.
4. After the renamed jobs execute once, select the emitted contexts for `Team delivery foundation` jobs
   `foundation-backend / validate` and `foundation-console / validate` in the GitHub UI. Confirm both are emitted by
   `.github/workflows/team-delivery-foundation.yml`; do not type speculative names or retain ambiguous generic
   `backend / validate` / `console / validate` contexts.
5. Do not require Playwright from this lightweight integration gate. Browser and accessibility certification belongs
   to workflows that genuinely execute those suites. Never label an executed failure as `not_run`.
6. Keep workflow permissions read-only by default, prevent bypass except for documented emergency administrators, and
   verify a test pull request cannot merge while either required check is absent, pending, cancelled, or failed.
7. Retain artifacts for the applicable certification period. Do not treat a local run or an artifact from another SHA
   as evidence for the candidate.

PR #162 (`Revert "Certify final hosted Data Product foundation"`) also requires an authenticated maintainer to comment
that it is superseded by the evidence-driven release model and close it without merging.
