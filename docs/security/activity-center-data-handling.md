# Activity Center data handling

All calls inherit authenticated trusted tenant/environment context. Switching either aborts requests, clears rendered results, and selects another session-storage scope. Seen storage contains only opaque provider keys and timestamps, is capped at 500 and expires after 24 hours/session. Hashing, if later used, is a matching aid—not anonymisation.

Telemetry permits low-cardinality interaction names, capability/activity type, provider outcome, count/duration buckets, and action. It rejects activity/entity/incident/case/workflow/approval/tenant/environment IDs, labels, titles, summaries, workflow names, and Watchlist identities. The drawer never renders raw JSON, errors, headers, SQL, credentials, workflow payloads or incident payloads. Generic activity performs no mutation.
