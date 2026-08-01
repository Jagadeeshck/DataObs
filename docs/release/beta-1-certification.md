# Beta 1 exact-commit certification

The machine-readable manifest names each capability producer, unique artifact,
schema, expected conclusion, required test categories, and mandatory status.
`verify_beta_candidate.py` accepts exactly one evidence record per capability
and checks repository, workflow, commit, artifact, producer SHA, schema,
terminal migration, versions and test summary. Missing mandatory evidence is
`pending`; it is never promoted to pass.

The dispatch-only candidate workflow checks out the requested SHA, runs contract,
security, release and chart gates, builds without pushing, generates SBOMs, and
scans before the separately permissioned publish job. Beta 1 is certified only
after that exact run and every mandatory producer succeeds. This document does
not declare Beta 1 certified or DataObs production ready.


## RC1 reconciliation

Schema 1.1 binds the integrated producer to the registry-derived terminal migration, exact dispatch SHA, skip-free mandatory categories, artifact hashes, and independent verification. The expected artifact is `dataobs-beta-1-rc1-integrated-certification`. PR #198 and hosted evidence are unresolved in this checkout, so the release is **NO_GO**, `functional_unvalidated`, and `not_published`.
