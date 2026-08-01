# Job and run observability backend

The backend projects canonical tenant-scoped jobs and runs from append-only OpenLineage evidence. Stable identifiers include tenant, environment, platform, namespace, name, and source run identity. Unfinished runs have a null duration.

Authoritative projections reuse migration `0008_job_run_observability`: fixed job, run, attempt, task, stage, and streaming-query indices plus the corresponding append-only data streams. Index names are selected by server code; callers cannot provide them. Every query is tenant and environment bound.

Canonical APIs under `/api/v1/jobs` and `/api/v1/runs` provide bounded lists and detail/evidence collections. The implementation is backend-only and does not provide a Console explorer, critical-path visualization, or comparison UI.
