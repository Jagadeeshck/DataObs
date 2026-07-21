# Capability status definitions

Implementation state and release readiness are independent. A `validated` capability does not make the whole product production-ready.

## Implementation states

- **validated** — executable and all applicable hosted, real-stack, browser, accessibility, security, scale and upgrade evidence has passed.
- **functional_unvalidated** — principal workflow is executable, but required validation evidence is missing.
- **foundation** — meaningful domain/storage/service/API implementation exists, but the user or operator workflow is incomplete.
- **scaffold** — placeholder, static example, interface, route shell or non-executable contract only.
- **not_started** — no meaningful implementation in the current product tree.
- **deprecated** — retained temporarily but outside the target architecture.
- **optional_integration** — interoperability/export path that is not an authoritative DataObs product plane.

## Release readiness

`blocked`, `internal_alpha`, `design_partner`, and `production_candidate` describe release readiness separately from implementation state.

## Validation dimensions

The independent dimensions are `unit`, `integration`, `real_stack`, `hosted_ci`, `browser`, `accessibility`, `security`, `scale`, `upgrade`, and `release`. Each is `passed`, `failed`, `defined_not_run`, `not_applicable`, or `missing`. A test definition is not a test execution; local execution is not hosted evidence.
