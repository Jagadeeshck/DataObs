# Team 0 security evidence orchestration repair — 2026-08-13

## Scope and repository state

The starting `main` snapshot was `e555eb706eda62981264e776847f0e74f5530a1c`. The supplied checkout had no Git
remote, so fetching a newer `main` was impossible; the task branch was reset from that supplied main snapshot. The final
task-branch SHA is the head SHA recorded by the pull request and Git commit metadata (a commit cannot truthfully embed
its own SHA in its contents).

The root `route-security-report.json`, `secret-handling-report.json`, `audit-safety-report.json`,
`workflow-security-report.json`, `security-posture-report.json`, `security-release-gate.json`, and
`security-evidence-verification.json` are retained historical/local review snapshots. They are not canonical inputs and
must never be treated as current CI evidence. Canonical policy remains under `docs/security`; CI-only output is created
under `security-runtime/`, which the generated-artifact policy forbids committing.

## Repair

Previously isolated jobs wrote reports to their own filesystems, while downstream fresh checkouts could package stale
root snapshots. The workflow now transfers named artifacts at every boundary:

```text
validation jobs
      |
      v
runtime security reports
      |
      v
posture evaluation
      |
      v
release-gate decision
      |
      v
exact-SHA evidence bundle
      |
      v
integrity verification
```

Assembly requires an explicit source directory and all mandatory reports. Every report SHA must equal the requested
40-character SHA. The manifest records repository, exact SHA, workflow/run/attempt/event, timestamp, environment class,
terminal migration, tool versions, inventory, and SHA-256 digests. Verification checks that complete inventory and
rejects missing files, digest changes, mixed SHAs, target/repository mismatch, incomplete provenance, and any attempt to
label same-workflow integrity checking as independent verification.

Posture evaluation is reporting: it may correctly produce `INCOMPLETE` without failing an ordinary PR workflow. Gate
generation records that decision but authorizes release only for `PASS`; its explicit `--enforce` mode fails closed for
`INCOMPLETE`, `UNVALIDATED`, and `FAIL`. GitHub-hosted execution is described as a CI integrity check, not hosted product
validation.

## Beta tenant-isolation assessment

The Beta workflow executes all of `tests/security` and `tests/certification` before attesting tenant isolation. That set
contains adversarial selector and cross-tenant isolation tests, including denial of unauthorized tenant selection. A
workflow regression test now binds the attestation to that executed suite. This does not create hosted certification.

## External state and remaining blockers

On 2026-08-13 the checkout had no remote and GitHub CLI was unauthenticated. Open PRs, Actions permissions/state,
rulesets, required checks, and workflow runs therefore could not be inspected. The precise administrator follow-up is in
`docs/operations/github-actions-release-gate-setup.md`. PR #162 could not be commented on or closed; an authenticated
maintainer must close it without merging using the prescribed obsolete-state comment.

Local validation covered compilation, repository gates, focused security/certification tests, the full test suite, and a
local exact-SHA build/verify/tamper simulation. Repository-wide Black and mypy retain pre-existing failures. Console
installation succeeded, but API generation was blocked by the installed Node 24 / Redocly dependency combination, so
the remaining chained console gates did not run; the final PR records individual command outcomes. Files changed are the
Team 0 workflow, evidence builder/verifier/gate scripts, generated artifact policy, orchestration regression tests,
Actions operations guidance, and this report.

Security truth is unchanged: posture `INCOMPLETE`; hosted controls verified `0`; independently verified `0`; blocking
findings `SECF-002` and `SECF-003`; hosted certification pending; supported platforms `[]`; production release `NO_GO`.
