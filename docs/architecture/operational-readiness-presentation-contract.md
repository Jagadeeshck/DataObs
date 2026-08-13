# Operational readiness presentation contract

- Preserve API states verbatim in meaning; formatting underscores as spaces is presentation only.
- `unknown` and absent values explicitly say evidence is unavailable and never become pass.
- `stale` displays “Current evidence: Stale”; a former result is not represented as current.
- `NO_GO` is a blocking release/readiness statement and is never softened.
- Severity does not imply a blocker. Only an explicit Team 0 gate state establishes the displayed relationship.
- Missing timestamps display “Not supplied”; the browser does not generate evaluation times.
- Provenance is limited to typed evidence references returned by the contract.
