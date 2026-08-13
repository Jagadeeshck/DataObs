# Platform lifecycle presentation contract

Lifecycle state is rendered verbatim with a human-readable label and never converted into health. Missing health is **Unknown**. Drift distinguishes no drift, drift detected, unknown, unavailable and not evaluated. Capacity distinguishes validated, unvalidated, unavailable and unknown; unvalidated is informational and never certified.

Relations are displayed only when returned as IDs by Team 0. Desired and observed fingerprints are evidence, not editable configuration. Revision is visible for operational correlation. Should mutation be introduced later, the browser must retain the ETag, use If-Match and one idempotency key per intentional action; conflicts must say “This resource changed since the page was loaded.” and must not retry automatically.
