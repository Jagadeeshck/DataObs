# Unified Activity Center

The Activity Center is a Team 5 presentation layer, not an alert or incident engine. Explicit permission-checked providers execute in parallel under a 2 second provider timeout and 4 second global deadline. Each returns at most 25 items; deterministic merging caps the page at 150. Context changes abort stale work. Partial results remain useful.

Ordering is occurrence time descending, then severity, stable capability order and activity key. Deduplication occurs only when providers supply the same canonical event identity. Forecasts must use observation time for feed placement.

`/activity` is lazy, protected by `console:read`, participates in Quick Find, and is not included in entity search. The authenticated shell offers an Activity presence button without background fan-out or a second polling loop. The page follows global time and refresh controls.
