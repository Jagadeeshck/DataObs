# GitHub Actions release-gate setup

Repository administration could not be inspected from the supplied checkout because no Git remote or authenticated
GitHub CLI session was available. An administrator must complete these steps; local validation is not hosted CI evidence.

As checked on 2026-08-13, this checkout still has no configured Git remote and `gh auth status` reports no authenticated
GitHub host. Consequently workflow active state, repository Actions permissions, rulesets, required checks, run history,
and PR-trigger suppression could not be queried. Do not interpret that limitation as evidence that Actions are disabled.

1. In **Settings → Actions → General**, allow Actions and permit the repository's required first-party actions.
2. In **Settings → Rules → Rulesets** (or **Branches → Branch protection rules**), create or edit the rule targeting
   `main`; require a pull request and require branches to be up to date before merging.
3. Run **Team delivery foundation** once on a pull request. Select emitted checks rather than typing speculative names.
4. Require exactly `Team delivery foundation / backend` and `Team delivery foundation / console`. Confirm both are
   emitted by `.github/workflows/team-delivery-foundation.yml` before enforcing the rule.
5. Do not require Playwright from this lightweight integration gate. Browser and accessibility certification belong to
   workflows that explicitly execute those suites; the foundation evidence records both as `not_run`.
6. Keep workflow permissions read-only by default, prevent bypass except for documented emergency administrators, and
   verify a test pull request cannot merge while either required check is absent, pending, cancelled, or failed.
7. Retain artifacts for the applicable certification period. Do not treat a local run or an artifact from another SHA
   as evidence for the candidate.

PR #162 (`Revert "Certify final hosted Data Product foundation"`) also requires an authenticated maintainer to comment
that it is superseded by the evidence-driven release model and close it without merging.
