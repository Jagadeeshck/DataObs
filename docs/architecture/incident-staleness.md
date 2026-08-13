# Incident staleness

Staleness policy `1.0.0` evaluates active response only. Incident age starts at `opened_at` and stops at the terminal transition for resolved/closed incidents. The staleness clock starts at `opened_at`, then moves only for events in the versioned `incident-meaningful-progress/1.0.0` allowlist. Watcher, tag, UI metadata, projection, and analytics writes are intentionally excluded.

States are `fresh`, `aging`, `stale`, `critically_stale`, and `unavailable`; thresholds belong to `IncidentStalenessPolicy`, not routes or UI.
