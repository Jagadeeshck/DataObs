---
name: product-planning
description: Translate the six-pillar DataObs vision into evidence-gated deliverable slices and roadmap prioritization.
---
# Product Planning

1. Read `.kiro/steering/product.md` and `docs/kiro/PRODUCT-VISION-AND-ROADMAP.md`.
2. Identify user, desired investigation outcome, pillar, existing code path and evidence level.
3. Read capability ledger and audit relevant implementation to classify: supported, functional unvalidated, scaffold, future.
4. Write problem, non-goals, API/data/UI touchpoints, tenant boundaries, SLO and confidence states.
5. Define incremental implementation: contract → real integration → Console → operations → release evidence.
6. Propose P0/P1/P2 and explicit dependencies. Avoid delivering all six pillars in v1.0.0.
**Output:** proposal, acceptance tests, dependencies, ledger/evidence changes and release-scope statement.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
