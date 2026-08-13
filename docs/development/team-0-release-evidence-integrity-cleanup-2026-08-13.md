# Team 0 release-evidence integrity cleanup — 2026-08-13

## Audit identity and posture

The supplied checkout had no configured Git remote, so fetching/rebasing `main` was not possible. The exact starting
integrated-main SHA was `786c18e69c49cc55bcf1349da803324c60cc7299` (merge of PR #284). The final branch SHA is the
commit containing this document and must be read factually with `git rev-parse HEAD`; it is not self-referentially
hard-coded into its own commit. No hosted run exists for that commit in this unauthenticated checkout.

The final decision remains **NO_GO**. Supported platforms remain `[]`; hosted, independent, browser/accessibility,
tenant-isolation, HA/DR, signing, and provenance certification remain pending unless their dedicated exact-SHA suites
actually execute and retained evidence is independently verified.

## Problems and fixes

* Console envelopes previously gave every named category an implicit pass. The envelope now supports `pass`, `fail`,
  `not_run`, and `blocked_external`; the reusable Console workflow records disabled browser/axe categories as `not_run`.
  Beta verification now requires each mandatory category to exist **and** have `status: pass`.
* Generic backend validation claimed tenant isolation was covered. Its default is now `not_run`. A caller must supply a
  dedicated adversarial test path, which the workflow executes successfully before it can materialise `pass`.
  Independent verification remains `pending`.
* The stale root `migration-graph-report.json` was generated output, so it was removed, ignored, and prohibited by the
  generated-artifact gate. Exact-SHA reports under dedicated evidence directories remain immutable history.
* Team 4's mutable AWS messaging input is now `evidence-template.json`. Its workflow creates artifact-only
  `hosted-evidence/evidence.json`, inserting the exact producer SHA and the executable terminal at that SHA.
* Current metadata validation checks current release surfaces, not historical `evidence.json` envelopes. Old envelopes
  retain the terminal that existed at their producer SHA and are never rewritten when the registry advances.
* Migration compatibility now describes the actual 0033 schema-intelligence indices, projections, runtime state, and
  append-only evidence. A regression test ties its terminal ID to the executable registry.
* SECF-001 retains its history but is resolved with the factual zero-finding workflow validator result. SECF-002 and
  SECF-003 remain open; security posture remains `INCOMPLETE` and release remains `NO_GO`.
* Canonical product audit metadata now identifies the integrated PR #284 repair SHA without changing readiness states.

## Generated-artifact classification

`migration-graph-report.json` is a generated local/CI report and forbidden at repository root. The similarly named
root files `broken-link-report.txt`, `capability-state-counts.json`, `capability-validation-report.json`,
`security-posture-report.json`, and `security-release-gate.json` are retained generated documentation/review snapshots
under existing canonical generators; this bounded cleanup does not silently delete or reclassify them. Canonical source
is YAML/configuration and generator code. Dedicated exact-SHA evidence directories are retained historical evidence.
New runtime/release reports must go to workflow output/evidence directories, never repository root.

## Validation and external status

The exact commands and results are recorded in the commit/PR validation summary. Browser installation/execution is not
claimed as passed unless actually run. GitHub Actions, rulesets, and PR #162 could not be inspected or changed because
the checkout has no remote and `gh auth status` reports no authentication. Administrator instructions are in
`docs/operations/github-actions-release-gate-setup.md`.

**Final release decision: NO_GO.**
