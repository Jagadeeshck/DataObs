# Data Quality Console operations

The Console reads canonical quality evidence at `/quality`. An unavailable card means the provider or request is unavailable; unknown means no conclusion exists; not configured means an optional provider is absent. Zero is shown only when the API measured and returned zero. Inspect the displayed source and observation timestamp before acting.

Monitor authoring is capability-driven and creates a draft. It accepts an opaque connection reference, never credentials or unrestricted SQL. Enablement is a separate confirmed operation. Run now returns an execution identifier and **queued** status only; use runtime evidence to establish eventual completion.

Lifecycle requests use the monitor ETag. On HTTP 412 the Console refreshes and requires the operator to review before retrying. Do not bypass this control. Archive, enable, and disable require confirmation. Tenant and environment are obtained from authenticated application context, not form data.

For incident investigation, open Findings in Monitor 360 and follow an incident link only when the backend supplies an incident identity. Absence of that identity does not mean absence of impact. If runtime or evidence APIs fail, preserve the request ID from the error and inspect API/runtime logs without logging tokens, connection references, or evidence payloads.

Rollback is an application deployment rollback; this feature has no migration. Canonical monitors created before rollback remain intact.
