# Capability promotion policy

Evidence is ranked: retained hosted CI; reproducible real stack; passing integration tests; passing focused unit tests; implementation; architecture/audit; PR description; issue/roadmap aspiration.

- `scaffold` → `foundation`: meaningful implementation exists.
- `foundation` → `functional_unvalidated`: the principal workflow executes.
- `functional_unvalidated` → `validated`: every applicable evidence dimension passed and retained.
- `deprecated`: replacement or removal guidance exists.
- `optional_integration`: interoperability only and not authoritative.

Every promotion updates evidence, blockers, next gate, audit date, and commit. A PR title, route, model, Compose file, or unexecuted test cannot promote a capability. Demotion is allowed when justified. Release readiness is reviewed separately.
