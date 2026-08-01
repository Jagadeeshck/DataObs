# Data Quality Console v1

The read-only Console owns `/quality` and `/quality/monitors/:monitorId`. Top-level URL-backed tabs cover overview, monitors, findings, recommendation proposals, coverage and runtime. Monitor 360 covers overview, observations, evaluations, baseline history, findings, incident relationships, suppressions, definition history and evidence.

Inventory filters include safe text search, state, monitor type, threshold mode, manager, creation source, target identifiers/source type, open findings, incident linkage and staleness. Signed cursors are bound to tenant, environment, route, filters and sort. Absence is preserved: measured zero is `0`; unknown is `null`; unavailable providers are not empty measured collections.

Enabled/active/learning/degraded/error monitors are stale after the last successful observation exceeds a bounded grace (default twice the schedule). Draft, disabled, suppressed and archived definitions are not assessed with active rules. A missing observation is unknown until schedule maturity can be established, and missing runtime evidence reduces confidence. Staleness is not failure and can never be presented as healthy.

Finding incident IDs establish a **direct relationship**, not causation or root cause. Other relationships are correlated, inferred or unknown. Coverage denominator zero is distinct from an unknown denominator, and not-configured coverage never displays as 0%. Missing runtime evidence is unavailable, never healthy.

The feature uses `quality:read` and `monitors:read`. It polls only when explicitly configured (default off), supports manual refresh and cancels requests on route or tenant/environment changes. Authoring, execution, baseline reset, suppression changes, recommendation decisions and remediation are deferred to `codex/quality-monitor-authoring-v1`.
