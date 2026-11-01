---
inclusion: auto
name: elastic-enterprise
description: Use this when designing or implementing features that use Elastic Enterprise license capabilities including ML anomaly detection, Watcher, Transform API, ESRE, field-level security, cross-cluster search, or Fleet integrations.
---

# Elastic Enterprise — DataObs integration rules

- DataObs targets the **Elastic Enterprise** license tier. All Enterprise X-Pack features
  are available: ML, Watcher, Transform, ESRE, FLS/DLS, CCS, Fleet.
- Local Docker stacks use `xpack.license.self_generated.type: trial` which activates all
  Enterprise features for 30 days. Use this for development and CI.
- **Never reference competitor product names** in code, comments, docs, or tests.
  Use neutral language: "anomaly detection", "data observability", "quality monitoring".
- When adding a feature that uses an Enterprise API, document the required license in the
  module docstring and in `.kiro/strategy/elastic-enterprise-features.md`.
- Enterprise features that require a separate model download (ELSER for ESRE) must include
  setup instructions in the relevant runbook under `docs/operations/`.
- ML anomaly detection jobs are lifecycle-managed with monitors: created on activate,
  stopped/deleted on deactivate/delete.
- Watcher watches are registered per monitor per tenant; IDs stored on monitor documents.
- Transforms are continuous (not one-shot); provision via migration with `defer_validation: true`.
- All new migrations are additive. Migration IDs `0001`–`0033` are immutable.
  Next available: `0034`.
- Full strategy context: `.kiro/strategy/elastic-enterprise-features.md`
- Product gaps and roadmap: `.kiro/strategy/product-gaps-and-roadmap.md`
